# Reserve and partial-pod planning / 预留与部分 Pod

Use the new offline Python tool, or ask the CLI: “使用 DGX B200 基准，在 500 MW
设施中预留 10% 运行功率和 20% 增长功率，均以设施总功率为基数。比较完整 Pod 与部分 Pod。”

```python
from agent import compare_allocations

data = compare_allocations({
    "parameters": {"facility_capacity_mw": 500},
    "use_baseline_defaults": True,
    "operating_reserve_pct": 10,
    "growth_reserve_pct": 20,
    "reserve_basis": "facility",
})
print(data["allocation"])
```

Percentages are planning inputs (10 means 10%), not required reliability margins.
Each must be finite and in [0,100]. Omission means zero. Operating reserve is a
percentage of nameplate facility MW. For growth choose **facility** (same base)
or **after_operating** (remaining facility MW). Both positive percentages require an
explicit basis. Additive reserves cannot exceed 100% together. A fully reserved
facility is valid and deploys zero racks. The response includes the budget,
component reserves, request/default sources and both plans; see reserve_inputs,
reserve_sources, inputs and provenance for the calculation assumptions.

Whole-pod allocation rounds down to complete pods. Partial allocation first
packs full pods and then complete, identical racks in at most one incomplete pod.
It does not permit fractional racks, servers or GPUs. Rack facility MW includes
server and external network power multiplied by PUE. No fixed pod-level overhead
or shared-infrastructure readiness is asserted. For each plan:
facility MW = operating reserve + growth reserve + used MW + packing remainder.
The remainder is deployable budget left after integer packing, not an intentional reserve.

运行预留按设施总 MW 计算，增长预留的基数由调用方选择。示例的两种口径分别得到
350 MW 和 360 MW 可部署预算；不替用户默认选择。只按整架增加，结果分开列出
完整 Pod 数与尾 Pod 的机架数。原工具保持只按完整 Pod 计算，不会隐式启用预留。
本次不包含机架场地约束、冷却/冗余验证或新图表。
