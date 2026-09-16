"""Strict API schemas for engineering tools and local knowledge. / 工程工具及本地知识的严格 API 契约。"""

from copy import deepcopy

from .schemas import COUNTS, PARAMETERS


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def parameter_schema(exclude_pue=False):
    return object_schema(
        {
            name: {
                "type": ["integer" if name in COUNTS else "number", "null"],
                "description": "Use null only when unspecified; defaults need explicit permission. / 未指定时用 null，默认值需明确允许。",
            }
            for name in PARAMETERS
            if not (exclude_pue and name == "pue")
        }
    )


def tool_definitions():
    capacity = {
        "parameters": parameter_schema(),
        "use_baseline_defaults": {"type": "boolean"},
    }
    scenario = object_schema(
        {
            "name": {"type": "string"},
            "kind": {"type": "string", "enum": ["named", "custom"]},
            **deepcopy(capacity),
        }
    )
    specs = [
        (
            "search_knowledge",
            "Retrieve sourced local explanations of PUE, server specs, rack/pod concepts, assumptions and scope. Not a calculator or live lookup. / 检索本地知识与来源，不计算部署结果或查询实时资料。",
            object_schema(
                {
                    "query": {"type": "string", "minLength": 1, "maxLength": 500},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 5},
                }
            ),
        ),
        (
            "calculate_capacity",
            "Calculate one deployment. Use the documented baseline only in an explicitly established baseline context. / 计算单个部署，仅在明确的基准上下文中使用默认值。",
            object_schema(capacity),
        ),
        (
            "compare_scenarios",
            "Compare at least two scenarios. Named scenarios use the catalog; custom scenarios use parameters. / 比较至少两个命名或自定义场景。",
            object_schema({"scenarios": {"type": "array", "items": scenario}}),
        ),
        (
            "run_pue_sensitivity",
            "Vary only PUE; other parameters fixed. Baseline step is available in context. / 仅扫描 PUE，其他参数固定。",
            object_schema(
                {
                    "parameters": parameter_schema(exclude_pue=True),
                    "use_baseline_defaults": {"type": "boolean"},
                    "pue_start": {"type": "number"},
                    "pue_end": {"type": "number"},
                    "step": {"type": ["number", "null"]},
                }
            ),
        ),
        (
            "generate_capacity_plot",
            "Plot a previous successful calculation using its result_id. Never supply or rewrite numerical rows. / 通过 result_id 绘制已有计算结果，不传入或重写数值。",
            object_schema(
                {
                    "result_id": {"type": "string"},
                    "analysis_type": {
                        "type": "string",
                        "enum": ["capacity", "comparison", "pue_sensitivity"],
                    },
                }
            ),
        ),
    ]
    return [
        {
            "type": "function",
            "name": name,
            "description": description,
            "parameters": schema,
            "strict": True,
        }
        for name, description, schema in specs
    ]


FINAL_SCHEMA = object_schema(
    {
        "kind": {
            "type": "string",
            "enum": ["answer", "knowledge", "clarification", "unsupported"],
        },
        "english": {"type": "string"},
        "chinese": {"type": "string"},
    }
)
