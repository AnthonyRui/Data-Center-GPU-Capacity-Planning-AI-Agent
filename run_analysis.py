"""Run from any directory. / 可从任意目录运行的分析入口。"""
import argparse
from pathlib import Path
from src.scenarios import load_scenarios, evaluate_scenarios, compare_references
from src.sensitivity import run_sensitivity
from src.plots import generate_figures

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="GPU capacity analysis / GPU容量分析")
    parser.add_argument("--parameters", type=Path, default=ROOT / "data/scenario_parameters.csv", help="Scenario CSV / 场景参数CSV")
    parser.add_argument("--sensitivity-config", type=Path, default=ROOT / "data/sensitivity_parameters.json", help="Sweep JSON / 扫描配置JSON")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="Root for results and figures / 结果和图表的输出根目录")
    args = parser.parse_args()
    configs = load_scenarios(args.parameters)
    baseline = next((inputs for row, inputs in configs if row["scenario"] == "Baseline"), None)
    if baseline is None:
        parser.error("A Baseline row is required / 必须存在Baseline场景行")
    results = evaluate_scenarios(args.parameters)
    sweeps = run_sensitivity(baseline, args.sensitivity_config)
    destination = args.output_dir / "results"
    destination.mkdir(parents=True, exist_ok=True)
    results.to_csv(destination / "scenario_results.csv", index=False, encoding="utf-8-sig")
    compare_references(results, ROOT / "data/original_scenario_references.csv").to_csv(destination / "reference_comparison.csv", index=False, encoding="utf-8-sig")
    for name, frame in sweeps.items():
        frame.to_csv(destination / (name + "_sensitivity.csv"), index=False, encoding="utf-8-sig")
    generate_figures(results, sweeps, args.output_dir / "figures")
    print(results[["scenario", "max_pods", "total_racks", "total_gpus", "remaining_capacity_mw"]].to_string(index=False))
    print("Analysis complete / 分析完成:", args.output_dir.resolve())


if __name__ == "__main__":
    main()
