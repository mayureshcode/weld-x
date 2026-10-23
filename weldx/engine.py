"""Bounded orchestration and fail-closed authorization; no physical actuation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import itertools
import json
import math
from pathlib import Path
import threading
import time
import uuid
from .model import Base, Configuration, canonical
from .validation import Check, Execution, GATES, Plan, Result, UnavailableAdapter
from .robustness import NOMINAL, Robustness, Trial, aggregate, scenarios

class Denied(RuntimeError):
    pass

class Journal:
    """Append-only hash-linked JSONL. Integrity checking, not tamper-proof storage."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events = []
        self.healthy = True
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                record = json.loads(line)
                digest = record.pop("digest")
                if record["sequence"] != len(self.events) + 1 or record["previous"] != self.head or digest != hashlib.sha256(canonical(record).encode()).hexdigest():
                    raise Denied("audit integrity check failed")
                self.events.append({**record, "digest": digest})
    @property
    def head(self):
        return self.events[-1]["digest"] if self.events else "0" * 64
    def append(self, kind, payload):
        import os
        record = {"sequence": len(self.events)+1, "previous": self.head,
                  "time_unix_s": time.time(), "kind": kind, "payload": payload}
        record["digest"] = hashlib.sha256(canonical(record).encode()).hexdigest()
        try:
            with self.path.open("a") as stream:
                stream.write(canonical(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            self.healthy = False
            raise
        self.events.append(record)
        return record

@dataclass(frozen=True)
class Evaluation:
    config_hash: str
    adapter_version: str
    phase: str
    nominal: Plan
    robustness: Robustness
    elapsed_s: float
    def status(self,config,adapter):
        if self.config_hash!=config.digest() or self.adapter_version!=adapter.version:return Result.UNKNOWN
        nominal=self.nominal.outcome(config,adapter.version)
        if nominal==Result.FAIL or self.robustness.outcome==Result.FAIL:return Result.FAIL
        return Result.PASS if self.qualifies(config,adapter) else Result.UNKNOWN
    def qualifies(self, config, adapter):
        return (self.config_hash == config.digest() and self.adapter_version == adapter.version
                and self.nominal.outcome(config, adapter.version) == Result.PASS
                and self.robustness.outcome == Result.PASS)

@dataclass(frozen=True)
class Candidate:
    id: str
    origin_hash: str
    configuration: Configuration
    evaluation: Evaluation
    relocation_m: float
    def classification(self, adapter):
        nominal = self.evaluation.nominal.outcome(self.configuration, adapter.version)
        if nominal == Result.FAIL:
            return "nominally_infeasible"
        if nominal == Result.UNKNOWN:
            return "validation_incomplete"
        robust = self.evaluation.robustness.outcome
        return "robustly_feasible" if robust == Result.PASS else (
            "nominally_feasible_not_robust" if robust == Result.FAIL else "validation_incomplete")

class Engine:
    def __init__(self, config: Configuration, journal: Journal, adapter=None):
        self.config = config
        self.original = config
        self.journal = journal
        self.adapter = adapter or UnavailableAdapter()
        self.lock = threading.RLock()
        self.stage = "IDLE"
        self.candidates = {}
        self.recommended = None
        self.approval = None
        self.final = None
        self.initial = None
        self.recoveries = 0
        self.last_search = None
        self.search_attempts = 0
        self.search_seconds = 0.0
        self.execution = None
        self.active_operation = None
        self.journal.append("session_started", {"configuration": config.model_dump(mode="json"),
                            "hash": config.digest(), "adapter": self.adapter.version,
                            "previous_authorization_restored": False})
    def _event(self, kind, payload):
        with self.lock:
            return self.journal.append(kind, payload)
    def _stage(self, name):
        self._event("workflow_transition", {"stage": name, "config_hash": self.config.digest()})
        self.stage = name
    def _check_snapshot(self, config):
        if self.config.digest() != config.digest():
            raise Denied("configuration changed during operation; result is stale")
    def _begin(self, name):
        with self.lock:
            if self.active_operation:
                raise Denied("another operation is active")
            self.active_operation = name
    def _end(self):
        with self.lock:
            self.active_operation = None
    def _plan(self, config, scenario, cancel, deadline):
        if cancel.is_set() or time.monotonic() >= deadline:
            return Plan(config.digest(), self.adapter.version, ())
        try:
            plan = self.adapter.validate(config, scenario, cancel, deadline)
            if not isinstance(plan, Plan):
                raise TypeError("adapter returned an invalid Plan contract")
            canonical(serial(plan))  # Reject nonfinite/unserializable backend evidence.
            if time.monotonic() >= deadline or cancel.is_set():
                return Plan(config.digest(), self.adapter.version, ())
            return plan
        except Exception as exc:
            # A failed backend call is UNKNOWN, never a successful validation.
            self._event("adapter_error", {"scenario": scenario.id, "type": type(exc).__name__, "message": str(exc)})
            return Plan(config.digest(), self.adapter.version, ())
    def evaluate(self, config, phase, cancel, deadline):
        start = time.monotonic()
        nominal = self._plan(config, NOMINAL, cancel, deadline)
        trials = []
        if nominal.outcome(config, self.adapter.version) == Result.PASS:
            if hasattr(self.adapter,"preflight_boundaries"):
                preflight=self.adapter.preflight_boundaries(config,phase,cancel,deadline)
                if any(t.outcome == Result.FAIL for t in preflight):
                    self._event("mandatory_boundary_rejected", {"config_hash":config.digest(),"phase":phase,
                        "tested":len(preflight),"failures":[serial(t) for t in preflight if t.outcome==Result.FAIL],
                        "mc_status":"not run: mandatory boundary failed; no success-rate claim"})
                    return Evaluation(config.digest(),self.adapter.version,phase,nominal,
                        aggregate(config,phase,preflight,self.adapter.version),time.monotonic()-start)
            # Mandatory complete-job boundaries precede Monte Carlo spending.
            ordered=sorted(scenarios(config,phase),key=lambda s:s.kind!="boundary")
            for scenario in ordered:
                if cancel.is_set() or time.monotonic() >= deadline:
                    break
                plan = self._plan(config, scenario, cancel, deadline)
                trials.append(Trial(scenario, plan, plan.outcome(config, self.adapter.version)))
        return Evaluation(config.digest(), self.adapter.version, phase, nominal,
                          aggregate(config, phase, trials,self.adapter.version), time.monotonic()-start)
    def detect(self, cancel=None):
        self._begin("detect")
        try:
            with self.lock:
                self.final = self.approval = self.recommended = None
            config = self.config
            result = self.evaluate(config, "heldout", cancel or threading.Event(),
                                   time.monotonic()+config.search.max_seconds)
            with self.lock:
                self._check_snapshot(config)
                self._event("initial_validation", serial(result))
                self.final = None
                self.initial = result
                self.approval = self.recommended = None
                self._stage("DETECT")
            return result
        finally:
            self._end()
    def search(self, cancel=None):
        self._begin("search")
        try:
            config = self.config
            cancel = cancel or threading.Event()
            start = time.monotonic()
            deadline = start + min(config.search.max_seconds, max(0,config.search.total_seconds-self.search_seconds))
            with self.lock:
                if self.stage not in ("DETECT", "STOPPED", "MAP", "RECOMMEND"):
                    raise Denied("detect or failed revalidation required before search")
                if self.search_attempts >= config.search.max_attempts or self.search_seconds >= config.search.total_seconds:
                    raise Denied("cumulative search budget exhausted")
                if self.recoveries >= config.max_recoveries:
                    raise Denied("recovery budget exhausted")
                self.search_attempts += 1
                self.approval = self.final = self.recommended = None
                self.candidates = {}
                self._stage("SEARCH")
            coarse_cap = max(1, int(config.search.max_candidates * (1-config.search.refinement_fraction)))
            coarse = iter(grid(config.search))
            fine = iter(())
            count = 0
            seen = set()
            for index in range(config.search.max_candidates):
                if cancel.is_set() or time.monotonic() >= deadline:
                    break
                if index == coarse_cap:
                    promising = sorted(self.candidates.values(), key=lambda c: rank_key(c, self.adapter, config))
                    fine = iter(refine(promising[:3], config.search))
                base = None
                for iterator in (fine, coarse):
                    for proposed in iterator:
                        key = (proposed.x_m, proposed.y_m, proposed.yaw_rad)
                        if key not in seen and config.search.contains(proposed):
                            base = proposed
                            seen.add(key)
                            break
                    if base is not None:
                        break
                if base is None:
                    break
                candidate_config = config.model_copy(update={"base": base})
                evaluation = self.evaluate(candidate_config, "search", cancel, deadline)
                candidate = Candidate(candidate_config.digest(), config.digest(), candidate_config,
                                      evaluation, math.hypot(base.x_m-config.base.x_m, base.y_m-config.base.y_m))
                with self.lock:
                    self._check_snapshot(config)
                    self._event("candidate_evaluated", serial(candidate))
                    self.candidates[candidate.id] = candidate
                count += 1
            with self.lock:
                self._check_snapshot(config)
                self.last_search = {"candidate_count": count, "elapsed_s": time.monotonic()-start,
                    "termination": "cancelled" if cancel.is_set() else "time_budget" if time.monotonic() >= deadline else "candidate_budget" if count >= config.search.max_candidates else "region_exhausted",
                    "bounds": config.search.model_dump(mode="json")}
                self.last_search.update(attempt=self.search_attempts,cumulative_search_seconds=self.search_seconds+self.last_search["elapsed_s"])
                self._event("search_finished", self.last_search)
                self._stage("MAP")
                qualified = [c for c in self.candidates.values() if c.evaluation.qualifies(c.configuration, self.adapter)]
                if qualified and not cancel.is_set():
                    best = min(qualified, key=lambda c: rank_key(c, self.adapter, config))
                    self.recommended = best.id
                    self._event("recommendation", {"candidate_id": best.id, "origin_hash": config.digest(),
                        "limits": self.last_search, "original_configuration": self.original.model_dump(mode="json"),
                        "original_failure_evidence": evaluation_summary(self.initial),
                        "proposed_base": best.configuration.base.model_dump(),"relocation_m": best.relocation_m,
                        "uncertainty_assumptions":best.configuration.uncertainty.model_dump(),
                        "nominal_and_robustness_evidence":evaluation_summary(best.evaluation),
                        "expected_benefit":"Qualifying tested placement under the declared simulation model; no independent fixture-error compensation is claimed.",
                        "limitations": "bounded search evidence only; explicit engineer approval and fresh exact held-out revalidation required"})
                    self._stage("RECOMMEND")
                else:
                    self._event("no_solution", {"message": "No robust placement found within the declared search bounds and computation budget.",
                        "evidence_status": "incomplete" if any(c.classification(self.adapter) == "validation_incomplete" for c in self.candidates.values()) else "tested",
                        "next_action": "Inspect failed/unknown constraints; restore missing backend or request engineer-authorized bounds/requirements change."})
            return self.last_search
        finally:
            if "start" in locals():
                self.search_seconds += time.monotonic()-start
            self._end()
    def approve(self, candidate_id, config_hash, engineer):
        with self.lock:
            if self.active_operation:
                raise Denied("operation active")
            candidate = self.candidates.get(candidate_id)
            if not isinstance(engineer,str) or not engineer.strip() or config_hash != self.config.digest() or candidate is None or candidate.origin_hash != config_hash or candidate_id != self.recommended or self.stage != "RECOMMEND":
                raise Denied("approval must reference current recommendation, job, configuration and engineer")
            if not candidate.evaluation.qualifies(candidate.configuration, self.adapter):
                raise Denied("candidate evidence does not qualify")
            approval = {"id": str(uuid.uuid4()), "candidate_id": candidate_id, "config_hash": config_hash,
                        "job_id": self.config.job.id, "engineer": engineer.strip(), "adapter_version": self.adapter.version}
            self._event("engineer_approved", approval)
            self.approval = approval
            self._stage("APPROVE")
            return approval
    def apply(self, approval_id, cancel=None):
        self._begin("apply")
        try:
            with self.lock:
                a=self.approval
                if not a or a["id"]!=approval_id or a["config_hash"]!=self.config.digest() or a["adapter_version"]!=self.adapter.version or self.stage!="APPROVE":
                    raise Denied("approval missing, stale or already consumed")
                c=self.candidates[a["candidate_id"]]
                if not c.evaluation.qualifies(c.configuration,self.adapter):
                    raise Denied("approved candidate evidence is stale")
                updated=Configuration.model_validate({**c.configuration.model_dump(mode="json"),"revision":self.config.revision+1})
                self._event("configuration_applied",{"approval":a,"configuration":updated.model_dump(mode="json"),
                    "hash":updated.digest(),"execution_authorization":"invalidated; synchronization pending"})
                self.config=updated;self.approval=self.final=None;self.recoveries+=1;self._stage("APPLY")
            cancel=cancel or threading.Event();deadline=time.monotonic()+updated.search.max_seconds
            try:
                binding=self.adapter.synchronize(updated,cancel,deadline)
            except Exception as exc:
                self._event("application_synchronization_error",{"type":type(exc).__name__,"message":str(exc)})
                binding=None
            with self.lock:
                self._check_snapshot(updated)
                confirmed=binding==updated.digest() and not cancel.is_set() and time.monotonic()<deadline
                self._event("application_synchronized" if confirmed else "application_synchronization_unconfirmed",
                    {"config_hash":updated.digest(),"execution_authorization":"invalidated; exact held-out revalidation required"})
                if not confirmed:self._stage("STOPPED")
            return updated
        finally:
            self._end()
    def revalidate(self, cancel=None):
        self._begin("revalidate")
        try:
            config = self.config
            with self.lock:
                if self.stage not in ("IDLE", "DETECT", "APPLY", "STOPPED"):
                    raise Denied("revalidation not allowed in current stage")
                self.final = None
                self._stage("REVALIDATE")
            cancel = cancel or threading.Event()
            deadline = time.monotonic()+config.search.max_seconds
            try:
                binding = self.adapter.synchronize(config, cancel, deadline)
            except Exception as exc:
                self._event("scene_synchronization_error", {"type": type(exc).__name__, "message": str(exc)})
                binding = None
            if binding == config.digest():
                result = self.evaluate(config, "heldout", cancel, deadline)
            else:
                result = Evaluation(config.digest(), self.adapter.version, "heldout",
                    Plan(config.digest(), self.adapter.version, ()), aggregate(config, "heldout", (),self.adapter.version), 0)
                self._event("scene_synchronization_unconfirmed", {"config_hash": config.digest()})
            with self.lock:
                self._check_snapshot(config)
                self._event("final_validation", serial(result))
                self.final = result
                self._stage("READY" if self.authorized() else "STOPPED")
            return result
        finally:
            self._end()
    def authorized(self):
        return bool(self.journal.healthy and self.adapter.ready and self.final and self.final.phase == "heldout"
                    and (not hasattr(self.adapter,"binding_valid") or self.adapter.binding_valid(self.config))
                    and self.final.qualifies(self.config, self.adapter))
    def execute(self, cancel=None):
        self._begin("execute")
        try:
            with self.lock:
                if self.stage != "READY" or not self.authorized():
                    raise Denied("execution denied: exact configuration has failed, unknown or stale mandatory gates")
                config = self.config
                plan = self.final.nominal
                self.final = None  # Single-use execution authorization, including errors.
                self._stage("EXECUTE")
            cancel = cancel or threading.Event()
            deadline = time.monotonic()+config.constraints.execution_timeout_s
            try:
                result = self.adapter.execute(config, plan, cancel, deadline)
                if not isinstance(result, Execution):
                    raise TypeError("adapter returned an invalid Execution contract")
                canonical(serial(result))
            except Exception as exc:
                self._event("execution_error", {"type": type(exc).__name__, "message": str(exc)})
                with self.lock:
                    self._stage("STOPPED")
                raise
            with self.lock:
                self._check_snapshot(config)
                valid = (not cancel.is_set() and time.monotonic() < deadline and result.success is True and result.cancelled is False
                         and result.config_hash == config.digest() and result.trajectory_id == plan.trajectory_id
                         and result.completed_segments == config.job.segments()
                         and isinstance(result.tracking_error_rad,(int,float)) and not isinstance(result.tracking_error_rad,bool)
                         and math.isfinite(result.tracking_error_rad)
                         and 0 <= result.tracking_error_rad <= config.constraints.max_tracking_error_rad)
                self._event("execution_finished", {"verified_complete": valid, "record": serial(result)})
                self.execution = result
                self._stage("COMPLETE" if valid else "STOPPED")
                return valid
        finally:
            self._end()
    def snapshot(self):
        with self.lock:
            return {"stage": self.stage, "configuration": self.config.model_dump(mode="json"),
                "original_base": self.original.base.model_dump(),
                "config_hash": self.config.digest(), "health": self.adapter.health(), "authorized": self.authorized(),
                "recommended": self.recommended, "approval": self.approval, "search": self.last_search,
                "candidates": [{"id": c.id, "base": c.configuration.base.model_dump(),
                    "classification": c.classification(self.adapter), "status": c.evaluation.status(c.configuration,self.adapter).value, "evidence": candidate_summary(c)} for c in self.candidates.values()],
                "initial": evaluation_summary(self.initial), "final": evaluation_summary(self.final), "execution": serial(self.execution),
                "audit": [{k: e[k] for k in ("sequence", "time_unix_s", "kind", "digest", "previous")} for e in self.journal.events],
                "presentation": "Summaries only; full immutable evidence is available through /api/evidence and /api/audit", "active_operation": self.active_operation}

def evaluation_summary(e):
    """Read-only presentation, never an input to any authorization gate.

    Keep the full nominal record; summarize repeated scenario checks without
    copying all plans or journal payloads into every polling response.
    """
    if e is None:
        return None
    trials=[]
    for t in e.robustness.trials:
        failed=[c for c in t.plan.checks if c.result == Result.FAIL]
        unknown=[c for c in t.plan.checks if c.result == Result.UNKNOWN]
        trials.append({"scenario": serial(t.scenario), "outcome": serial(t.outcome),
            "summary_checks": serial(failed or unknown[:1]), "evidence_kind": t.evidence_kind,
            "execution_evidence": serial(t.plan.execution_evidence),
            "check_count": len(t.plan.checks), "trajectory_id": t.plan.trajectory_id})
    return {"config_hash": e.config_hash, "adapter_version": e.adapter_version,
        "phase": e.phase, "elapsed_s": e.elapsed_s, "nominal": serial(e.nominal),
        "robustness": {"phase": e.robustness.phase, "outcome": serial(e.robustness.outcome),
            "groups": serial(e.robustness.groups), "trials": trials},
        "presentation": "Scenario check summaries, not complete Plan records"}

def candidate_summary(c):
    return {"id": c.id, "origin_hash": c.origin_hash,
        "configuration": c.configuration.model_dump(mode="json"),
        "evaluation": evaluation_summary(c.evaluation), "relocation_m": c.relocation_m}

def axis_values(axis):
    count = math.floor((axis.maximum-axis.minimum)/axis.step + 1e-10) + 1
    for i in range(count):
        value = axis.minimum + i * axis.step
        if value <= axis.maximum + 1e-12:
            yield min(value, axis.maximum)

def grid(search):
    # Lazy, deterministic, space-spreading grid traversal. A row-major prefix
    # previously exhausted small budgets along one edge of the installation region.
    axes=(search.x_m,search.y_m,search.yaw_rad)
    counts=tuple(math.floor((a.maximum-a.minimum)/a.step+1e-10)+1 for a in axes)
    total=math.prod(counts);bits=(total-1).bit_length()
    center=tuple((n-1)//2 for n in counts)
    center_linear=(center[0]*counts[1]+center[1])*counts[2]+center[2]
    def point(linear):
        ix,remainder=divmod(linear,counts[1]*counts[2]);iy,iz=divmod(remainder,counts[2])
        values=[min(a.maximum,a.minimum+i*a.step) for a,i in zip(axes,(ix,iy,iz))]
        return Base(x_m=values[0],y_m=values[1],yaw_rad=values[2])
    yield point(center_linear)
    if total==1:return
    for index in range(1<<bits):
        linear=int(format(index,'0'+str(bits)+'b')[::-1],2)
        if linear<total and linear!=center_linear:yield point(linear)

def refine(candidates, search):
    for c in candidates:
        b = c.configuration.base
        for dx, dy, dyaw in itertools.product((-0.5, 0, 0.5), repeat=3):
            if dx == dy == dyaw == 0:
                continue
            proposed = Base(x_m=b.x_m+dx*search.x_m.step, y_m=b.y_m+dy*search.y_m.step,
                            yaw_rad=b.yaw_rad+dyaw*search.yaw_rad.step)
            if search.contains(proposed):
                yield proposed

def rank_key(candidate, adapter, origin):
    feasible = candidate.evaluation.qualifies(candidate.configuration, adapter)
    groups = candidate.evaluation.robustness.groups
    lower = min((g.wilson95[0] for g in groups if g.wilson95), default=0)
    delta = origin.search.robustness_comparable_delta
    # Predeclared fixed bands avoid non-transitive pairwise "comparable" sorting.
    band = math.floor(lower/delta + 1e-12) if delta else lower
    margins = [c.margin for c in candidate.evaluation.nominal.checks if c.constraint == "joint_limits" and c.margin is not None and math.isfinite(c.margin)]
    return (not feasible, -band, candidate.relocation_m, -lower, -min(margins, default=0), candidate.id)

def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Configuration):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {k: serial(getattr(value, k)) for k in value.__dataclass_fields__}
    raise TypeError(type(value).__name__)


def _audited_operation(fn):
    from functools import wraps
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Denied as exc:
            self._event("operation_rejected", {"operation": fn.__name__, "reason": str(exc)})
            raise
    return wrapped

for _name in ("detect", "search", "approve", "apply", "revalidate", "execute"):
    setattr(Engine, _name, _audited_operation(getattr(Engine, _name)))
