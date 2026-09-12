"""Strict JSON-compatible tool contracts. / 严格的 JSON 兼容工具契约。"""

from dataclasses import dataclass, field, fields
from decimal import Decimal
from itertools import pairwise
from math import isfinite
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Literal, TypedDict

from src.power_model import ModelInputs

PARAMETERS = tuple(item.name for item in fields(ModelInputs))
COUNTS = {"gpus_per_server", "servers_per_rack", "racks_per_pod"}
MAX_SCENARIOS = 50
MAX_PUE_POINTS = 10000


class ToolValidationError(ValueError):
    """Invalid input; messages never echo the supplied values. / 输入无效，不回显输入值。"""


class MissingParametersError(ToolValidationError):
    def __init__(self, names: list[str]):
        self.missing_fields = names
        super().__init__(
            "Missing parameters; provide values or explicitly enable baseline defaults / "
            "缺少参数，请提供数值或显式允许使用基准默认值: " + ", ".join(names)
        )


class SourceInfo(TypedDict):
    origin: Literal["user_input", "public_specification", "scenario_assumption"]
    used_default: bool
    source: str


class CapacityResult(TypedDict):
    tool: str
    result: dict[str, int | float]
    provenance: dict[str, SourceInfo]
    assumptions_used: list[str]
    units: dict[str, str]
    explanation: dict[str, str]


def object_fields(
    value: Any, allowed: set[str], required: set[str] | None = None
) -> dict:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ToolValidationError("Expected an object / 必须为对象")
    if set(value) - allowed:
        raise ToolValidationError("Unknown fields are not allowed / 不允许未知字段")
    if required and required - set(value):
        raise ToolValidationError("Required fields are missing / 缺少必填字段")
    return value


def number(value: Any, name: str, minimum: float = 0, strict: bool = False) -> None:
    if type(value) not in (int, float):
        raise ToolValidationError(f"{name}: numeric value required / 必须为数值")
    try:
        valid = isfinite(value) and (value > minimum if strict else value >= minimum)
    except OverflowError:
        valid = False
    if not valid:
        raise ToolValidationError(
            f"{name}: invalid finite value or range / 数值非有限或超出范围"
        )


def validate_parameters(value: Any) -> dict[str, int | float]:
    value = object_fields(value, set(PARAMETERS))
    for name, item in value.items():
        if name in COUNTS:
            if type(item) is not int or item < 1:
                raise ToolValidationError(
                    f"{name}: positive integer required / 必须为正整数"
                )
        else:
            number(
                item,
                name,
                minimum=1 if name == "pue" else 0,
                strict=name in {"facility_capacity_mw", "server_power_kw"},
            )
    return dict(value)


def label(value: Any) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 64
        or not value.isprintable()
    ):
        raise ToolValidationError(
            "Name must contain 1–64 printable characters / 名称须为 1–64 个可打印字符"
        )


@dataclass(frozen=True, kw_only=True)
class CapacityRequest:
    parameters: dict[str, int | float] = field(default_factory=dict)
    use_baseline_defaults: bool = False

    def __post_init__(self):
        validate_parameters(self.parameters)
        if type(self.use_baseline_defaults) is not bool:
            raise ToolValidationError(
                "Default policy must be boolean / 默认值策略必须为布尔值"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "CapacityRequest":
        return cls(**object_fields(value, {"parameters", "use_baseline_defaults"}))


@dataclass(frozen=True, kw_only=True)
class ScenarioRequest:
    name: str
    parameters: dict[str, int | float] = field(default_factory=dict)
    use_baseline_defaults: bool = False

    def __post_init__(self):
        label(self.name)
        CapacityRequest(
            parameters=self.parameters, use_baseline_defaults=self.use_baseline_defaults
        )

    @classmethod
    def from_dict(cls, value: Any) -> "ScenarioRequest":
        return cls(
            **object_fields(
                value, {"name", "parameters", "use_baseline_defaults"}, {"name"}
            )
        )


@dataclass(frozen=True, kw_only=True)
class ComparisonRequest:
    scenarios: list[str | ScenarioRequest]

    def __post_init__(self):
        if (
            not isinstance(self.scenarios, list)
            or not 2 <= len(self.scenarios) <= MAX_SCENARIOS
        ):
            raise ToolValidationError("Provide 2–50 scenarios / 请提供 2–50 个场景")
        names = []
        for item in self.scenarios:
            if isinstance(item, str):
                label(item)
                names.append(item)
            elif isinstance(item, ScenarioRequest):
                item.__post_init__()
                names.append(item.name)
            else:
                raise ToolValidationError("Invalid scenario / 场景格式无效")
        if len(names) != len(set(names)):
            raise ToolValidationError(
                "Scenario names must be unique / 场景名称必须唯一"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "ComparisonRequest":
        value = object_fields(value, {"scenarios"}, {"scenarios"})
        items = value["scenarios"]
        if not isinstance(items, list):
            raise ToolValidationError("Scenarios must be a list / 场景必须为列表")
        return cls(
            scenarios=[
                ScenarioRequest.from_dict(item) if isinstance(item, dict) else item
                for item in items
            ]
        )


@dataclass(frozen=True, kw_only=True)
class PueSensitivityRequest(CapacityRequest):
    pue_start: float
    pue_end: float
    step: float

    def __post_init__(self):
        super().__post_init__()
        if "pue" in self.parameters:
            raise ToolValidationError(
                "Specify PUE through the sweep range only / PUE 请仅通过扫描范围指定"
            )
        number(self.pue_start, "pue_start", minimum=1)
        number(self.pue_end, "pue_end", minimum=1)
        number(self.step, "step", strict=True)
        if self.pue_end < self.pue_start:
            raise ToolValidationError(
                "PUE end must be at least start / PUE 终点不能小于起点"
            )
        start, end, step = (
            Decimal(str(v)) for v in (self.pue_start, self.pue_end, self.step)
        )
        if (end - start) / step >= MAX_PUE_POINTS:
            raise ToolValidationError(
                "PUE sweep exceeds 10000 points / PUE 扫描不能超过 10000 个点"
            )

    def values(self) -> list[float]:
        self.__post_init__()
        start, end, step = (
            Decimal(str(v)) for v in (self.pue_start, self.pue_end, self.step)
        )
        count = int((end - start) / step) + 1
        values = [float(start + i * step) for i in range(count)]
        if any(b <= a for a, b in pairwise(values)):
            raise ToolValidationError(
                "Step is below numerical resolution / 步长小于数值分辨率"
            )
        return values

    @classmethod
    def from_dict(cls, value: Any) -> "PueSensitivityRequest":
        required = {"pue_start", "pue_end", "step"}
        return cls(
            **object_fields(
                value, required | {"parameters", "use_baseline_defaults"}, required
            )
        )


@dataclass(frozen=True, kw_only=True)
class PlotRequest:
    analysis_type: Literal["capacity", "comparison", "pue_sensitivity"]
    result_data: list[dict[str, Any]]
    output_path: str

    def __post_init__(self):
        if self.analysis_type not in ("capacity", "comparison", "pue_sensitivity"):
            raise ToolValidationError("Unsupported plot type / 不支持此图表类型")
        if (
            not isinstance(self.result_data, list)
            or not 1 <= len(self.result_data) <= MAX_PUE_POINTS
        ):
            raise ToolValidationError(
                "Plot requires 1–10000 result rows / 图表需要 1–10000 行结果"
            )
        if any(not isinstance(row, dict) for row in self.result_data):
            raise ToolValidationError("Plot rows must be objects / 图表行必须为对象")
        if not isinstance(self.output_path, str) or not self.output_path:
            raise ToolValidationError(
                "A relative PNG path is required / 必须提供相对 PNG 路径"
            )
        # Enforce the same path policy on Windows and Linux. / Windows 和 Linux 使用相同规则。
        posix, windows = (
            PurePosixPath(self.output_path),
            PureWindowsPath(self.output_path),
        )
        if (
            posix.is_absolute()
            or windows.drive
            or windows.root
            or "\\" in self.output_path
            or ".." in posix.parts
            or any(c in self.output_path for c in ':*?"<>|')
            or any(
                not part.isprintable() or part.endswith((" ", "."))
                for part in posix.parts
            )
            or any(PureWindowsPath(part).is_reserved() for part in posix.parts)
            or posix.suffix.lower() != ".png"
        ):
            raise ToolValidationError(
                "Use a safe relative .png path / 请使用安全的相对 .png 路径"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "PlotRequest":
        required = {"analysis_type", "result_data", "output_path"}
        return cls(**object_fields(value, required, required))


def parse_request(value: Any, schema: type):
    if type(value) is schema:
        value.__post_init__()  # Validate mutable nested objects again. / 重新校验可变的嵌套对象。
        return value
    return schema.from_dict(value)
