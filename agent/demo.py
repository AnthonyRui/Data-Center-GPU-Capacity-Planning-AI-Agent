"""Scripted offline demonstration, not natural-language inference. / 预设离线演示，不进行自然语言推理。"""

import json

from .llm_client import ModelReply, ToolCall
from .schemas import PARAMETERS

QUESTIONS = {
    "baseline": "Plan a 500 MW DGX B200 deployment using the baseline PUE.",
    "custom": "Use baseline DGX B200 specifications with 300 MW, PUE 1.25, four servers per rack and 32 racks per pod.",
    "comparison": "Using the baseline, compare PUE 1.15, 1.20 and 1.30.",
    "sensitivity": "Using the baseline, show GPU capacity for PUE 1.10 to 1.60 and generate a chart.",
    "unsupported": "What breaker size and transformer should I install?",
}


def parameters(**values):
    return {key: values.get(key) for key in PARAMETERS}


class DemoClient:
    def __init__(self, case):
        self.case, self.index = case, 0

    def complete(self, history, instructions, tools):
        self.index += 1
        name, args = None, None
        if self.index == 1 and self.case in {"baseline", "custom"}:
            name = "calculate_capacity"
            values = (
                {"facility_capacity_mw": 500}
                if self.case == "baseline"
                else {
                    "facility_capacity_mw": 300,
                    "pue": 1.25,
                    "servers_per_rack": 4,
                    "racks_per_pod": 32,
                }
            )
            args = {"parameters": parameters(**values), "use_baseline_defaults": True}
        elif self.index == 1 and self.case == "comparison":
            name = "compare_scenarios"
            args = {
                "scenarios": [
                    {
                        "kind": "custom",
                        "name": f"PUE {value}",
                        "parameters": parameters(pue=value),
                        "use_baseline_defaults": True,
                    }
                    for value in (1.15, 1.2, 1.3)
                ]
            }
        elif self.case == "sensitivity" and self.index <= 2:
            if self.index == 1:
                name = "run_pue_sensitivity"
                args = {
                    "parameters": {key: None for key in PARAMETERS if key != "pue"},
                    "use_baseline_defaults": True,
                    "pue_start": 1.1,
                    "pue_end": 1.6,
                    "step": None,
                }
            else:
                name = "generate_capacity_plot"
                args = {"analysis_type": "pue_sensitivity", "result_id": "result_1"}
        if name:
            return ModelReply(
                calls=[ToolCall(f"demo_{self.index}", name, json.dumps(args))]
            )
        unsupported = self.case == "unsupported"
        return ModelReply(
            text=json.dumps(
                {
                    "kind": "unsupported" if unsupported else "answer",
                    "english": "Detailed electrical equipment sizing is outside this model."
                    if unsupported
                    else "The registered engineering tools computed the results below. Review the declared defaults and scope.",
                    "chinese": "电气设备详细选型超出当前模型范围。"
                    if unsupported
                    else "以下结果由注册工程工具计算，请查看已注明的默认参数与模型范围。",
                },
                ensure_ascii=False,
            )
        )
