# Model assumptions / 模型假设

## Parameter basis / 参数依据

Server power and GPU count follow the public NVIDIA DGX B200 specifications. Facility capacity, rack layout, network power, pod size and PUE are explicit planning assumptions. Scenario benchmarks are retained separately from editable inputs.

服务器功率与GPU数量依据NVIDIA DGX B200公开规格。设施容量、机架布局、网络功率、Pod规模与PUE均作为明确的规划假设，场景基准值与可编辑输入分开保留。

## Reconstruction / 重建说明

For Conservative, the new example assumes 14.3 kW/server, 3 servers/rack, 1.2 kW external network/rack and 24 racks/pod. This yields 44.1 kW/rack and 1.0584 MW IT/pod. At PUE 1.25, facility power is 1.323 MW/pod and 377 whole pods fit.

保守场景新增示例假设为14.3 kW/台、3台/机架、1.2 kW外部网络/机架、24机架/Pod，得到44.1 kW/机架、1.0584 MW IT/Pod；PUE为1.25时，每Pod设施功率为1.323 MW，最多容纳377个完整Pod。

For High-Density, the new example assumes 5 servers/rack, 2.0 kW external network/rack and 32 racks/pod. This yields 73.5 kW/rack and 2.352 MW IT/pod. At PUE 1.15, facility power is 2.7048 MW/pod and 184 whole pods fit.

高密度场景新增示例假设为5台/机架、2.0 kW外部网络/机架、32机架/Pod，得到73.5 kW/机架、2.352 MW IT/Pod；PUE为1.15时，每Pod设施功率为2.7048 MW，最多容纳184个完整Pod。

These examples reproduce the displayed references but are not uniquely determined by them. Their inputs are illustrative design assumptions, not measured deployment data. The PUE values and output references themselves are explicitly present in the source table.

这些示例复现了原表显示值，但原表无法唯一确定这些输入。这些输入为示例设计假设，不是实测部署数据。PUE值与输出参考值本身则明确出现在原表中。

## Physical and operating interpretation / 物理与运行解释

The NVIDIA DGX B200 is 10U. Five such systems need 50U and six need 60U before additional rack equipment. Even the four-server baseline requires separate checks for external networking, cooling, weight and service clearance. These density sweeps are mathematical sensitivity cases, not installation instructions. [NVIDIA hardware and mechanical specifications](https://docs.nvidia.com/dgx/dgxb200-user-guide/introduction-to-dgxb200.html).

DGX B200为10U，五台需要50U、六台需要60U，尚未计入其他机架设备。四台基准配置也需另行核验外部网络、冷却、重量及维护空间。密度扫描仅用于数学敏感性分析，不是安装指导。来源见上述NVIDIA规格。

PUE is applied as a constant planning multiplier. A real facility's PUE varies with load and operating conditions.

PUE在模型中作为固定规划乘数；真实设施PUE随负载及运行条件变化。

The original baseline allocates facility power to complete pods. The optional [allocation comparison](reserve-allocation.md) deducts explicit operating and growth reserves before packing whole pods or whole racks. Residual deployable power is not an operating reserve.

原基准按完整 Pod 分配设施功率。可选分配对比工具先扣除显式预留，再按整 Pod 或整架装填；装填后的剩余功率不是运行预留。
