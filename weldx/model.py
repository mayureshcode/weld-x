"""Immutable, unit-explicit input schema and content-addressed configuration."""
from __future__ import annotations
import hashlib
import json
import math
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Finite = Annotated[float, Field(allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]

class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

class Pose(Frozen):
    x_m: Finite = 0
    y_m: Finite = 0
    z_m: Finite = 0
    roll_rad: Finite = 0
    pitch_rad: Finite = 0
    yaw_rad: Finite = 0

class Base(Frozen):
    x_m: Finite
    y_m: Finite
    yaw_rad: Finite = 0

class Axis(Frozen):
    minimum: Finite
    maximum: Finite
    step: Positive
    @model_validator(mode="after")
    def ordered(self):
        if not math.isfinite(self.maximum-self.minimum) or not math.isfinite((self.maximum-self.minimum)/self.step):
            raise ValueError("axis span / resolution must be finite")
        if self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self

class Search(Frozen):
    x_m: Axis
    y_m: Axis
    yaw_rad: Axis
    max_candidates: Annotated[int, Field(strict=True, ge=1, le=10000)] = 32
    max_seconds: Annotated[float, Field(gt=0, le=3600)] = 30
    max_attempts: Annotated[int, Field(strict=True, ge=1, le=10)] = 3
    total_seconds: Annotated[float, Field(gt=0, le=36000)] = 90
    refinement_fraction: Annotated[float, Field(gt=0, lt=1)] = 0.25
    robustness_comparable_delta: Annotated[float, Field(ge=0, le=1)] = 0.02
    def contains(self, base: Base) -> bool:
        return all(a.minimum <= v <= a.maximum for a, v in
                   [(self.x_m, base.x_m), (self.y_m, base.y_m), (self.yaw_rad, base.yaw_rad)])

class Seam(Frozen):
    frame: Literal["workpiece"] = "workpiece"
    id: Annotated[str, Field(min_length=1)]
    points_m: Annotated[tuple[tuple[Finite, Finite, Finite], ...], Field(min_length=2, max_length=1000)]
    tool_rpy_rad: tuple[Finite, Finite, Finite]
    approach_m: Positive = 0.03
    retreat_m: Positive = 0.03
    weld_speed_m_s: Positive = 0.01

class Job(Frozen):
    id: Annotated[str, Field(min_length=1)]
    seams: Annotated[tuple[Seam, ...], Field(min_length=1, max_length=20)]
    @model_validator(mode="after")
    def unique_ids(self):
        if len({s.id for s in self.seams}) != len(self.seams):
            raise ValueError("seam IDs must be unique")
        return self
    def segments(self) -> tuple[str, ...]:
        out = []
        for i, seam in enumerate(self.seams):
            if i:
                out.append(f"{self.seams[i-1].id}->{seam.id}:transition")
            out.extend(f"{seam.id}:{phase}" for phase in ("approach", "weld", "retreat"))
        return tuple(out)

class Uncertainty(Frozen):
    distribution: Literal["independent_uniform_bounded"] = "independent_uniform_bounded"
    base_translation_m: Nonnegative = 0.002
    base_yaw_rad: Nonnegative = 0.01
    fixture_translation_m: Nonnegative = 0.002
    fixture_yaw_rad: Nonnegative = 0.01
    model_tcp_translation_m: Nonnegative = 0.001
    model_tcp_yaw_rad: Nonnegative = 0.005
    mc_count: Annotated[int, Field(strict=True, ge=1, le=10000)] = 20
    min_mc_count: Annotated[int, Field(strict=True, ge=1, le=10000)] = 20
    success_threshold: Annotated[float, Field(gt=0, le=1)] = 0.95
    search_seed: Annotated[int, Field(strict=True, ge=0)] = 1701
    heldout_seed: Annotated[int, Field(strict=True, ge=0)] = 2903
    @model_validator(mode="after")
    def independent_seeds(self):
        if self.search_seed == self.heldout_seed:
            raise ValueError("search and held-out seeds must differ")
        return self

class Constraints(Frozen):
    position_tolerance_m: Positive = 0.001
    orientation_tolerance_rad: Positive = 0.02
    minimum_clearance_m: Nonnegative = 0.005
    max_joint_velocity_rad_s: Positive = 1.0
    max_joint_acceleration_rad_s2: Positive = 2.0
    planning_timeout_s: Annotated[float, Field(gt=0, le=60)] = 5.0
    execution_timeout_s: Annotated[float, Field(gt=0, le=3600)] = 120.0
    max_tracking_error_rad: Positive = 0.02
    access_required: bool = True

class Configuration(Frozen):
    schema_version: Literal[1] = 1
    revision: Annotated[int, Field(strict=True, ge=1)] = 1
    units: Literal["SI:m,rad,s"] = "SI:m,rad,s"
    frame_convention: Literal["world:REP-103;poses:fixed-XYZ-RPY"] = "world:REP-103;poses:fixed-XYZ-RPY"
    robot: Literal["ABB_IRB_120_PROVISIONAL"] = "ABB_IRB_120_PROVISIONAL"
    model_version: Annotated[str, Field(min_length=1)] = "unverified"
    software_version: Annotated[str, Field(min_length=1)] = "weld-x/0.1.0"
    base_height_m: Finite = 0
    base: Base
    workpiece: Pose
    fixture: Pose
    tcp: Pose
    job: Job
    constraints: Constraints = Constraints()
    uncertainty: Uncertainty = Uncertainty()
    search: Search
    max_recoveries: Annotated[int, Field(strict=True, ge=0, le=10)] = 2
    def digest(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json")).encode()).hexdigest()

def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
