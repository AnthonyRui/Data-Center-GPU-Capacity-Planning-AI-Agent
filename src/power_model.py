"""Pure power-budget calculations; kW at rack level, MW above it.
纯功率预算计算：机架层使用 kW，Pod 和设施层使用 MW。
"""
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_FLOOR
from math import isfinite
from numbers import Integral


def _number(value, name, minimum=0, strict=False):
    if isinstance(value, bool):
        raise ValueError(f"{name}: numeric value required / 必须为数值")
    try:
        valid = isfinite(value) and (value > minimum if strict else value >= minimum)
    except TypeError:
        valid = False
    if not valid:
        raise ValueError(f"{name}: invalid finite value / 数值无效或超出范围")


def _count(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name}: integer >= {minimum} required / 必须为规定范围内的整数")


def _d(value):
    return Decimal(str(value))


@dataclass(frozen=True)
class ModelInputs:
    """Baseline planning defaults. / 默认基准规划参数。"""
    facility_capacity_mw: float = 500.0
    server_power_kw: float = 14.3
    gpus_per_server: int = 8
    servers_per_rack: int = 4
    network_power_kw: float = 1.5
    racks_per_pod: int = 32
    pue: float = 1.20

    def __post_init__(self):
        _number(self.facility_capacity_mw, "facility_capacity_mw", strict=True)
        _number(self.server_power_kw, "server_power_kw", strict=True)
        _number(self.network_power_kw, "network_power_kw")
        _number(self.pue, "pue", minimum=1)
        for name in ("gpus_per_server", "servers_per_rack", "racks_per_pod"):
            _count(getattr(self, name), name)


def calculate_rack_power(server_power_kw, servers_per_rack, network_power_kw):
    """Return rack IT kW, including external network. / 返回含外部网络的机架 IT kW。"""
    _number(server_power_kw, "server_power_kw", strict=True)
    _count(servers_per_rack, "servers_per_rack")
    _number(network_power_kw, "network_power_kw")
    return float(_d(server_power_kw) * int(servers_per_rack) + _d(network_power_kw))


def calculate_pod_power(rack_it_power_kw, racks_per_pod):
    """Return pod IT MW. / 返回 Pod IT 功率，单位 MW。"""
    _number(rack_it_power_kw, "rack_it_power_kw", strict=True)
    _count(racks_per_pod, "racks_per_pod")
    return float(_d(rack_it_power_kw) * int(racks_per_pod) / 1000)


def calculate_facility_power(it_power_mw, pue):
    """Return facility MW including PUE overhead. / 返回包含 PUE 开销的设施 MW。"""
    _number(it_power_mw, "it_power_mw")
    _number(pue, "pue", minimum=1)
    return float(_d(it_power_mw) * _d(pue))


def calculate_max_pods(facility_capacity_mw, pod_facility_power_mw):
    """Floor whole pods without rounding displayed MW first.
    按完整 Pod 向下取整，不先对显示用 MW 四舍五入。
    """
    _number(facility_capacity_mw, "facility_capacity_mw")
    _number(pod_facility_power_mw, "pod_facility_power_mw", strict=True)
    return int((_d(facility_capacity_mw) / _d(pod_facility_power_mw)).to_integral_value(rounding=ROUND_FLOOR))


def calculate_gpu_capacity(max_pods, racks_per_pod, servers_per_rack, gpus_per_server):
    """Return GPU count in complete pods. / 返回完整 Pod 中的 GPU 总数。"""
    _count(max_pods, "max_pods", minimum=0)
    for name, value in (("racks_per_pod", racks_per_pod), ("servers_per_rack", servers_per_rack), ("gpus_per_server", gpus_per_server)):
        _count(value, name)
    return int(max_pods * racks_per_pod * servers_per_rack * gpus_per_server)


def calculate_remaining_capacity(facility_capacity_mw, used_capacity_mw):
    """Signed MW margin; negative means overload. / 有符号剩余 MW，负数表示超限。"""
    _number(facility_capacity_mw, "facility_capacity_mw")
    _number(used_capacity_mw, "used_capacity_mw")
    return float(_d(facility_capacity_mw) - _d(used_capacity_mw))


def evaluate(inputs):
    """Evaluate a validated configuration. / 计算经过验证的配置。"""
    rack = calculate_rack_power(inputs.server_power_kw, inputs.servers_per_rack, inputs.network_power_kw)
    pod_it = calculate_pod_power(rack, inputs.racks_per_pod)
    pod_facility = calculate_facility_power(pod_it, inputs.pue)
    pods = calculate_max_pods(inputs.facility_capacity_mw, pod_facility)
    used = float(_d(pod_facility) * pods)
    deployed_it = float(_d(pod_it) * pods)
    return {
        **asdict(inputs),
        "rack_it_power_kw": rack,
        "pod_it_power_mw": pod_it,
        "pod_facility_power_mw": pod_facility,
        "max_it_capacity_mw": float(_d(inputs.facility_capacity_mw) / _d(inputs.pue)),
        "max_pods": pods,
        "total_racks": pods * inputs.racks_per_pod,
        "total_gpus": calculate_gpu_capacity(pods, inputs.racks_per_pod, inputs.servers_per_rack, inputs.gpus_per_server),
        "deployed_it_power_mw": deployed_it,
        "used_capacity_mw": used,
        "remaining_capacity_mw": calculate_remaining_capacity(inputs.facility_capacity_mw, used),
        "capacity_utilization_pct": used / inputs.facility_capacity_mw * 100,
        "deployed_overhead_mw": float(_d(used) - _d(deployed_it)),
    }
