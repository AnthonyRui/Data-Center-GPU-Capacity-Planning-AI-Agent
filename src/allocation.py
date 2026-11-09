"""Facility reserve accounting and allocation in whole racks (exact decimal ratios)."""

from fractions import Fraction
from math import isfinite


def _percent(value, name):
    if type(value) not in (int, float) or not 0 <= value <= 100 or not isfinite(value):
        raise ValueError(f"{name} must be a finite percentage in [0, 100]")
    return Fraction(str(value)) / 100


def allocation_plans(
    inputs,
    operating_reserve_pct=0,
    growth_reserve_pct=0,
    reserve_basis=None,
    rack_limit=None,
):
    """Compare both policies under one explicit budget; a partial pod contains whole racks."""
    op = _percent(operating_reserve_pct, "operating_reserve_pct")
    growth = _percent(growth_reserve_pct, "growth_reserve_pct")
    if reserve_basis not in (None, "facility", "after_operating"):
        raise ValueError("reserve_basis must be facility or after_operating")
    if op and growth and reserve_basis is None:
        raise ValueError(
            "Choose reserve_basis: facility (additive) or after_operating (sequential)"
        )
    capacity = Fraction(str(inputs.facility_capacity_mw))
    operating_mw = capacity * op
    growth_mw = (
        capacity - operating_mw if reserve_basis == "after_operating" else capacity
    ) * growth
    budget = capacity - operating_mw - growth_mw
    if budget < 0:
        raise ValueError("Combined facility reserves exceed 100%")
    rack_mw = (
        (
            Fraction(str(inputs.server_power_kw)) * inputs.servers_per_rack
            + Fraction(str(inputs.network_power_kw))
        )
        * Fraction(str(inputs.pue))
        / 1000
    )
    if rack_limit is not None and (type(rack_limit) is not int or rack_limit < 0):
        raise ValueError("rack_limit must be a nonnegative integer or null")
    power_racks = budget // rack_mw
    max_racks = power_racks if rack_limit is None else min(power_racks, rack_limit)
    limit = (
        "power"
        if rack_limit is None or power_racks < rack_limit
        else "rack_space"
        if rack_limit < power_racks
        else "both"
    )
    space_mw = (power_racks - max_racks) * rack_mw

    def plan(racks):
        pods, extra = divmod(racks, inputs.racks_per_pod)
        used = racks * rack_mw
        return {
            "whole_pods": pods,
            "racks_in_partial_pod": extra,
            "total_racks": racks,
            "total_gpus": racks * inputs.servers_per_rack * inputs.gpus_per_server,
            "used_facility_mw": float(used),
            "packing_remainder_mw": float(budget - used - space_mw),
            "space_limited_unused_mw": float(space_mw),
            "remaining_deployable_mw": float(budget - used),
        }

    return {
        "power_limit_racks": power_racks,
        "rack_limit": rack_limit,
        "feasible_racks": max_racks,
        "limiting_constraint": limit,
        "operating_reserve_mw": float(operating_mw),
        "growth_reserve_mw": float(growth_mw),
        "deployable_facility_mw": float(budget),
        "rack_facility_mw": float(rack_mw),
        "whole_pod": plan(max_racks // inputs.racks_per_pod * inputs.racks_per_pod),
        "partial_pod": plan(max_racks),
    }
