# OpsAI capacity-module integration / 容量模块接入计划

Prepared: 2026-11-02. Status: local integration preparation implemented and tested;
see [development record](development-progress.md). The OpsAI application itself
is not yet implemented.

## Today's scope / 今日范围

Prepare the existing deterministic capacity tools for reuse by an OpsAI application.
Reuse `examples/phase1a_tools.py`, which already runs without an API key; do not
introduce another calculation engine or claim a Dashboard already exists.

1. Document the four tool contracts: inputs, units, explicit baseline opt-in,
   validation errors, result/provenance fields, and trusted plot output directory.
2. Add or adapt a minimal application-facing example that imports the tools
   without configuring an LLM. Preserve existing CLI entry points.
3. Verify that direct model evaluation and tool-based application calls agree
   for baseline and a custom configuration, and that invalid inputs fail clearly.
4. Update README to explain the capacity module's role and the planned separation
   between operational analysis and capacity planning. Record actual checks.
5. Commit/push only validated, relevant files and check GitHub Actions.

今日只整理接口、无 AI 调用示例、回归验证和接入说明。现有公式与 CLI 保留。
不在本轮实现 Dashboard、异常检测、Reserve 或 Partial Pod。

## Acceptance / 验收

- No API key or network model request is needed to run the integration example.
- Baseline remains 221 whole pods, 7,072 racks, 226,304 GPUs, and 1.84832 MW
  integer-packing remainder for the documented 500 MW, PUE 1.2 configuration.
- Existing tests pass; application-facing checks cover useful interface behavior.
- Errors and parameter provenance remain visible to the caller.
- Documentation labels future OpsAI functionality as planned, not delivered.

## Subsequent integration / 后续接入

OpsAI will initially present operational analysis and capacity planning as separate
features. CPU utilization does not directly imply GPU demand or facility power.
Operational datasets are not present in the current capacity scenario files;
synthetic data must be labelled as demonstration data.

Reserve arithmetic remains awaiting user confirmation and does not block this
interface work. No public deployment, repository migration or rename is required
for this increment.
