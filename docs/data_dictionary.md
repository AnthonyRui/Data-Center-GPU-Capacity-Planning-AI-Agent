# Data dictionary / 数据字典

`scenario_parameters.csv` holds editable inputs, `original_scenario_references.csv` holds rounded historical references, and `results/*.csv` contains generated values. Input provenance is retained in scenario outputs. / 参数CSV保存可编辑输入，原始参考CSV保存历史舍入值，`results/*.csv`保存生成值；场景输出保留来源信息。

| Column / 列 | Meaning and unit / 含义及单位 |
| --- | --- |
| `scenario` | Unique scenario name / 唯一场景名称 |
| `facility_capacity_mw` | Total facility power budget, >0 MW / 设施总功率预算，>0 MW |
| `server_power_kw` | Whole-server power, >0 kW / 整机功率，>0 kW |
| `gpus_per_server` | Positive integer GPUs/server / 每台GPU正整数数量 |
| `servers_per_rack` | Positive integer servers/rack / 每机架服务器正整数数量 |
| `network_power_kw` | External network power per rack, ≥0 kW / 每机架外部网络功率，≥0 kW |
| `racks_per_pod` | Positive integer racks/pod / 每Pod机架正整数数量 |
| `pue` | Facility power divided by IT power, ≥1 / 设施功率与IT功率之比，≥1 |
| `input_status` | `original_baseline` or `reconstructed_assumption` / 原基准或新增重建假设 |
| `notes_en`, `notes_zh` | English and Chinese provenance / 中英文来源说明 |
| `rack_it_power_kw` | Rack IT power including external networking / 含外部网络的机架IT kW |
| `pod_it_power_mw` | IT MW per pod / 每Pod IT MW |
| `pod_facility_power_mw` | Facility MW per pod / 每Pod设施MW |
| `max_it_capacity_mw` | Continuous upper IT budget before whole-pod packing / 完整Pod装填前的连续IT功率上限 |
| `max_pods` | Maximum whole pods / 最大完整Pod数量 |
| `total_racks` | Racks within those pods / 这些Pod内的机架数量 |
| `total_gpus` | GPUs within those pods / 这些Pod内的GPU数量 |
| `deployed_it_power_mw` | IT power of deployed whole pods / 已部署完整Pod的IT MW |
| `used_capacity_mw` | Facility power of deployed whole pods / 已部署完整Pod的设施MW |
| `remaining_capacity_mw` | Capacity minus used power / 总容量减已用功率，MW |
| `capacity_utilization_pct` | Used facility power / capacity × 100; not GPU utilization / 设施功率容量利用率，不是GPU利用率 |
| `deployed_overhead_mw` | Used facility MW minus deployed IT MW / 已用设施MW减已部署IT MW |
| `varied_parameter` | Input varied in a sensitivity sweep / 敏感性扫描中变化的参数 |
| `metric` | Quantity being compared with original references / 与原参考值比较的指标 |
| `calculated`, `reference` | New full-precision output and original displayed value / 新计算完整精度值与原显示值 |
| `matches_display_precision` | Equality after rounding to the original decimal places / 按原小数位数舍入后是否一致 |
| `source` | Reference source location / 参考来源位置 |

All numeric inputs must be finite. Nonpositive counts and fractional counts are rejected. / 所有数值输入必须有限；非正数量或非整数数量会被拒绝。
