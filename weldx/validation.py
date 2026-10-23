"""Trusted adapter contract. UNKNOWN and missing evidence never pass a gate."""
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import math
from .model import Configuration, canonical

class Result(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"

GATES = ("reachability", "ik", "joint_limits", "collision", "continuity",
         "tcp_tolerance", "access", "dynamics", "timing", "controller")

@dataclass(frozen=True)
class Check:
    segment: str
    constraint: str
    result: Result
    reason: str
    measurement: float | None = None
    margin: float | None = None

def scenario_digest(scenario):
    return hashlib.sha256(canonical(asdict(scenario)).encode()).hexdigest()

@dataclass(frozen=True)
class ScenarioExecution:
    """Trusted observer receipt, not a planning request or a sensor specification."""
    config_hash: str
    adapter_version: str
    scenario_hash: str
    trajectory_id: str
    completed_segments: tuple[str, ...]
    feedback_samples_per_segment: tuple[int, ...]
    maximum_tracking_error_rad: float
    maximum_tcp_error_m: float
    maximum_orientation_error_rad: float
    restored: bool
    observer: str
    observed_segments: tuple[str, ...] = ()
    def observed(self,config,scenario,plan):
        segments=self.observed_segments or self.completed_segments
        return bool(self.config_hash==config.digest() and self.adapter_version==plan.adapter_version
            and self.scenario_hash==scenario_digest(scenario) and self.trajectory_id==plan.trajectory_id
            and segments and segments==config.job.segments()[:len(segments)]
            and len(self.feedback_samples_per_segment)==len(segments)
            and all(isinstance(n,int) and not isinstance(n,bool) and n>0 for n in self.feedback_samples_per_segment)
            and self.restored is True and self.observer.strip()
            and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0
                for v in (self.maximum_tracking_error_rad,self.maximum_tcp_error_m,self.maximum_orientation_error_rad)))
    def confirms(self, config, scenario, plan):
        measurements=(self.maximum_tracking_error_rad,self.maximum_tcp_error_m,self.maximum_orientation_error_rad)
        limits=(config.constraints.max_tracking_error_rad,config.constraints.position_tolerance_m,config.constraints.orientation_tolerance_rad)
        return bool(self.observed(config,scenario,plan) and self.config_hash == config.digest() and self.adapter_version == plan.adapter_version
            and self.scenario_hash == scenario_digest(scenario) and self.trajectory_id == plan.trajectory_id
            and self.completed_segments == config.job.segments()
            and len(self.feedback_samples_per_segment) == len(self.completed_segments)
            and all(isinstance(n,int) and not isinstance(n,bool) and n>0 for n in self.feedback_samples_per_segment)
            and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
                and 0<=v<=limit+1e-12 for v,limit in zip(measurements,limits))
            and self.restored is True and bool(self.observer.strip()))

@dataclass(frozen=True)
class Plan:
    config_hash: str
    adapter_version: str
    checks: tuple[Check, ...]
    trajectory_id: str | None = None
    execution_evidence: ScenarioExecution | None = None
    def outcome(self, config: Configuration, adapter_version: str) -> Result:
        if self.config_hash != config.digest() or self.adapter_version != adapter_version:
            return Result.UNKNOWN
        expected = {(s, gate) for s in config.job.segments() for gate in GATES}
        actual = [(c.segment, c.constraint) for c in self.checks]
        if set(actual) != expected or len(actual) != len(expected):
            return Result.UNKNOWN
        if any(not c.reason or any(v is not None and not math.isfinite(v) for v in (c.measurement,c.margin)) for c in self.checks):
            return Result.UNKNOWN
        if any(c.result == Result.FAIL for c in self.checks):
            return Result.FAIL
        if not self.trajectory_id or any(c.result != Result.PASS for c in self.checks):
            return Result.UNKNOWN
        return Result.PASS

@dataclass(frozen=True)
class Execution:
    config_hash: str
    trajectory_id: str
    completed_segments: tuple[str, ...]
    success: bool
    cancelled: bool
    tracking_error_rad: float | None
    reason: str

class UnavailableAdapter:
    """Production default. There is deliberately no pretend robotics backend."""
    version = "unavailable:ros2-jazzy-gazebo-harmonic-moveit2"
    ready = False
    def health(self):
        return {"adapter": "unavailable", "ros": "not_connected", "gazebo": "not_connected",
                "moveit": "not_connected", "controllers": "not_connected",
                "robot_model": "provisional", "execution": "blocked"}
    def synchronize(self, config, cancel, deadline):
        return None
    def validate(self, config, scenario, cancel, deadline):
        return Plan(config.digest(), self.version, tuple(
            Check(segment, gate, Result.UNKNOWN, "ROS/Gazebo/MoveIt adapter not connected")
            for segment in config.job.segments() for gate in GATES))
    def execute(self, config, plan, cancel, deadline):
        raise RuntimeError("simulation backend unavailable; execution denied")
