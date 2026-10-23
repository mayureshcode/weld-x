"""Declared test design. Perturbations are passed to ONE robotics adapter."""
from dataclasses import dataclass
import itertools
import math
import random
from .model import Configuration, canonical
from .validation import Result, Plan

SOURCES = ("base", "fixture", "model", "combined")

@dataclass(frozen=True)
class Scenario:
    id: str
    source: str
    kind: str
    seed: int
    # dx, dy, dz, dyaw. Base has fixed nominal z; base dz uncertainty is zero.
    base: tuple[float, float, float, float] = (0, 0, 0, 0)
    fixture: tuple[float, float, float, float] = (0, 0, 0, 0)
    model: tuple[float, float, float, float] = (0, 0, 0, 0)

NOMINAL = Scenario("nominal", "none", "nominal", 0)

def scenarios(config: Configuration, phase: str):
    if phase not in ("search", "heldout"):
        raise ValueError("phase must be search or heldout")
    u = config.uncertainty
    seed = u.search_seed if phase == "search" else u.heldout_seed
    ranges = {"base": (u.base_translation_m, u.base_translation_m, 0, u.base_yaw_rad),
              "fixture": (u.fixture_translation_m,) * 3 + (u.fixture_yaw_rad,),
              "model": (u.model_tcp_translation_m,) * 3 + (u.model_tcp_yaw_rad,)}
    for group_index, source in enumerate(SOURCES):
        active = tuple(ranges) if source == "combined" else (source,)
        dims = [(name, i, size) for name in active for i, size in enumerate(ranges[name]) if size]
        vectors = []
        # Each signed axis extreme, plus two opposite joint corners. Not all corners.
        for name, axis, size in dims:
            for sign in (-1, 1):
                vectors.append({(name, axis): sign * size})
        for sign in (-1, 1):
            vectors.append({(name, axis): sign * size for name, axis, size in dims})
        # Independent installation and fixture errors can oppose one another.
        # Same-sign corners alone miss the largest relative translation. Include
        # all eight opposed planar corners / fixture-height extremes explicitly.
        if source == 'combined' and u.base_translation_m and u.fixture_translation_m:
            for sx,sy,sz in itertools.product((-1,1),repeat=3):
                vectors.append({('base',0):sx*u.base_translation_m,
                    ('base',1):sy*u.base_translation_m,
                    ('fixture',0):-sx*u.fixture_translation_m,
                    ('fixture',1):-sy*u.fixture_translation_m,
                    ('fixture',2):sz*u.fixture_translation_m})
        for index, vector in enumerate(vectors):
            values = {name: [0.0] * 4 for name in ranges}
            for (name, axis), value in vector.items():
                values[name][axis] = value
            yield Scenario(f"{phase}:{source}:boundary:{index}", source, "boundary", seed,
                           **{k: tuple(v) for k, v in values.items()})
        rng = random.Random(seed + 1009 * group_index)
        for index in range(u.mc_count):
            values = {name: [0.0] * 4 for name in ranges}
            for name, axis, size in dims:
                values[name][axis] = rng.uniform(-size, size)
            yield Scenario(f"{phase}:{source}:mc:{index}", source, "mc", seed,
                           **{k: tuple(v) for k, v in values.items()})

@dataclass(frozen=True)
class Trial:
    scenario: Scenario
    plan: Plan
    outcome: Result

@dataclass(frozen=True)
class GroupSummary:
    source: str
    boundary_tested: int
    boundary_expected: int
    boundary_passed: int
    mc_tested: int
    mc_expected: int
    mc_passed: int
    mc_unknown: int
    empirical_rate: float | None
    wilson95: tuple[float, float] | None
    outcome: Result

@dataclass(frozen=True)
class Robustness:
    phase: str
    trials: tuple[Trial, ...]
    groups: tuple[GroupSummary, ...]
    outcome: Result

def wilson(passed, tested):
    if not tested:
        return None
    z = 1.959963984540054
    p = passed / tested
    center = (p + z*z / (2*tested)) / (1 + z*z/tested)
    half = z * math.sqrt(p*(1-p)/tested + z*z/(4*tested*tested)) / (1 + z*z/tested)
    return max(0, center-half), min(1, center+half)

def aggregate(config, phase, trials):
    expected = tuple(scenarios(config, phase))
    groups = []
    unique = len({t.scenario.id for t in trials}) == len(trials)
    expected_by_id = {s.id: s for s in expected}
    intact = unique and all(expected_by_id.get(t.scenario.id) == t.scenario for t in trials)
    for source in SOURCES:
        ex = [s for s in expected if s.source == source]
        ts = [t for t in trials if t.scenario.source == source]
        b = [t for t in ts if t.scenario.kind == "boundary"]
        mc = [t for t in ts if t.scenario.kind == "mc"]
        be = sum(s.kind == "boundary" for s in ex)
        me = sum(s.kind == "mc" for s in ex)
        bp = sum(t.outcome == Result.PASS for t in b)
        mp = sum(t.outcome == Result.PASS for t in mc)
        unknown = sum(t.outcome == Result.UNKNOWN for t in mc)
        rate = mp / len(mc) if mc and not unknown else None
        if not intact:
            outcome = Result.UNKNOWN
        elif any(t.outcome == Result.FAIL for t in b):
            outcome = Result.FAIL
        elif len(b) != be or len(mc) != me or unknown or any(t.outcome == Result.UNKNOWN for t in b) or len(mc) < config.uncertainty.min_mc_count:
            outcome = Result.UNKNOWN
        elif bp != be or rate < config.uncertainty.success_threshold:
            outcome = Result.FAIL
        else:
            outcome = Result.PASS
        groups.append(GroupSummary(source, len(b), be, bp, len(mc), me, mp, unknown,
                                   rate, wilson(mp, len(mc)) if not unknown else None, outcome))
    outcome = Result.PASS if all(g.outcome == Result.PASS for g in groups) else (
        Result.FAIL if any(g.outcome == Result.FAIL for g in groups) else Result.UNKNOWN)
    return Robustness(phase, tuple(trials), tuple(groups), outcome)
