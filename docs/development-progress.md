# Development record / 开发记录

## 2026-11-09 — Reserve and partial-pod allocation

Added the optional `compare_allocations` tool. Both reserve conventions are supported explicitly; original whole-pod behavior is unchanged. Partial allocation uses complete racks only. The 102-test local suite passed, including reserve validation, budget conservation, exact rack boundaries, baseline regression and agent integration. See [usage and assumptions](reserve-allocation.md). Physical rack-space constraints and new plots remain planned.

## 2026-11-02 — Capacity-module integration preparation

Implemented local application example `examples/opsai_capacity.py` using the
existing dispatcher, without duplicating model arithmetic. It preserves validation
errors, units, assumptions and provenance. The existing four-tool example and CLI
remain available. Added the integration guide and clarified README scope.

Validation on Python 3.12:

- `python -m unittest discover -s tests -q`: **97 tests passed** (94 existing,
  3 new application integration tests).
- New checks compare baseline and explicit custom inputs with direct model
  evaluation, preserve missing/invalid input errors, and run the example in a
  fresh process from a different directory while blocking LLM imports and sockets.
- Baseline: 221 whole pods, 7,072 racks, 226,304 GPUs, 1.84832 MW remaining.
- `python -m ruff check examples/opsai_capacity.py tests/test_opsai_integration.py`:
  passed. `git diff --check`: passed before commit.
- Initial new subprocess test exposed Windows console encoding differences;
  explicit UTF-8 interpreter mode fixed the test transport. All checks above
  refer to the corrected run.

本轮只完成接入准备，未发布 Dashboard、运营分析模型或新的容量约束。
没有调用付费 AI 服务，没有修改原有计算公式或场景数据。

Next: define the narrow operational-analysis proposal and data contract, then
prepare clearly labelled synthetic demonstration data. The user confirmed there
is no separate CPU forecasting classroom repository. Do not keep requesting it.
Reserve semantics remain pending and block only reserve-dependent extensions.
The latest project URL is
https://github.com/AnthonyRui/Data-Center-GPU-Capacity-Planning-AI-Agent;
old and new URLs resolved to the same HEAD before this change.

Remote CI evidence should be checked against the actual pushed commit in GitHub
Actions; local success alone does not establish a successful remote workflow.
