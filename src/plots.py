"""Reproducible Matplotlib figures with bilingual captions. / 可重复生成的图表及双语说明。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text
from matplotlib import font_manager
import numpy as np

COLORS = ["#477b91", "#13695d", "#c77836"]


def configure_style():
    """Use installed Chinese fonts when available. / 优先使用可用中文字体。"""
    available = {f.name for f in font_manager.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "Noto Sans CJK SC", "SimHei", "WenQuanYi Zen Hei"]
    chosen = next((name for name in candidates if name in available), None)
    plt.rcParams.update({"font.family": ([chosen, "DejaVu Sans"] if chosen else ["DejaVu Sans"]),
                         "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlepad": 16,
                         "figure.facecolor": "#fafbf9", "axes.facecolor": "#fafbf9",
                         "axes.unicode_minus": False, "savefig.dpi": 180})
    return chosen is not None


def generate_figures(results, sweeps, output_dir):
    """Save chart assets; fixed units on each axis. / 保存图表，各轴明确标注单位。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    chinese = configure_style()

    def label(en, zh):
        return en + "\n" + zh if chinese else en

    def save(fig, name, note=None):
        if note:
            fig.text(0.08, 0.025, note, fontsize=8, color="#56616a")
        fig.tight_layout(rect=(0, 0.09 if note else 0, 1, 1))
        fig.savefig(output_dir / (name + ".png"))
        # English README gets English chart variants. / 英文README使用英文图表版本。
        if name in {"scenario_comparison", "gpu_capacity_vs_pue"}:
            english_dir = output_dir / "readme_en"
            english_dir.mkdir(exist_ok=True)
            for artist in fig.findobj(match=Text):
                artist.set_text(artist.get_text().split("\n")[0])
            fig.savefig(english_dir / (name + ".png"))
        plt.close(fig)

    b = results.loc[results.scenario == "Baseline"].iloc[0]
    foot = label("Illustrative reconstruction for non-baseline cases; see assumptions.", "非基准场景采用新增重建假设，详见模型说明。")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    server_kw = b.server_power_kw * b.servers_per_rack
    ax.barh([0], [server_kw], color=COLORS[1], label=label("Server systems", "服务器系统"))
    ax.barh([0], [b.network_power_kw], left=[server_kw], color=COLORS[2], label=label("External network", "外部网络"))
    ax.set(yticks=[], xlabel="kW / rack", title=label("Baseline rack power", "基准机架功率构成"))
    ax.text(server_kw / 2, 0, f"{server_kw:g} kW", ha="center", color="white")
    ax.set_xlim(0, b.rack_it_power_kw * 1.15)
    ax.text(b.rack_it_power_kw + 0.6, 0, f"{b.rack_it_power_kw:g} kW", va="center")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.5), ncol=2)
    save(fig, "rack_power_breakdown")

    fig, ax = plt.subplots(figsize=(9, 5.4))
    racks = np.arange(1, 65)
    ax.plot(racks, racks * b.rack_it_power_kw / 1000, label="IT", color=COLORS[0])
    ax.plot(racks, racks * b.rack_it_power_kw / 1000 * b.pue, label=label("Facility", "设施"), color=COLORS[1])
    ax.set(xlabel=label("Racks per pod", "每Pod机架数"), ylabel="MW / pod", title=label("Pod power scales with rack count", "Pod功率随机架数线性增长"))
    ax.legend()
    save(fig, "pod_power_scaling")

    fig, ax = plt.subplots(figsize=(9, 5.4))
    pods = np.arange(int(b.max_pods * 1.15) + 2)
    ax.plot(pods, pods * b.pod_facility_power_mw, color=COLORS[1])
    ax.axhline(b.facility_capacity_mw, color=COLORS[2], ls="--", label=f"{b.facility_capacity_mw:g} MW limit")
    ax.scatter([b.max_pods], [b.used_capacity_mw], color=COLORS[2], zorder=3)
    ax.annotate(f"{int(b.max_pods)} pods / {b.used_capacity_mw:.2f} MW", (b.max_pods, b.used_capacity_mw), xytext=(-160, -45), textcoords="offset points", arrowprops={"arrowstyle": "->"})
    ax.set(xlabel=label("Whole pods", "完整Pod数量"), ylabel="Facility MW", title=label("Baseline facility capacity", "基准设施容量约束"))
    ax.legend()
    save(fig, "facility_capacity")

    fig, ax = plt.subplots(figsize=(9, 5.4))
    bars = ax.bar(results.scenario, results.remaining_capacity_mw, color=COLORS)
    ax.bar_label(bars, fmt="%.3f", padding=4)
    ax.set_ylim(0, max(results.remaining_capacity_mw) * 1.25)
    ax.set(ylabel="Remaining MW", title=label("Unused capacity after whole-pod deployment", "完整Pod部署后的剩余容量"))
    save(fig, "remaining_capacity", foot)

    fig, axes = plt.subplots(1, 3, figsize=(13, 5.4))
    for ax, metric, title in zip(axes, ["pod_facility_power_mw", "max_pods", "total_gpus"],
                               [label("Facility MW / pod", "每Pod设施功率"), label("Whole pods", "完整Pod数"), label("GPU count", "GPU数量")]):
        bars = ax.bar(np.arange(len(results)), results[metric], color=COLORS)
        ax.set_xticks(np.arange(len(results)), results.scenario, rotation=20)
        ax.bar_label(bars, labels=[f"{v:,.2f}" if metric == "pod_facility_power_mw" else f"{v:,.0f}" for v in results[metric]], padding=4, fontsize=9)
        ax.set_ylim(0, max(results[metric]) * 1.22)
        ax.set_title(title)
    save(fig, "scenario_comparison", foot)

    p = sweeps["pue"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.3))
    for ax, metric, title in zip(axes, ["max_it_capacity_mw", "max_pods"], [label("Maximum IT capacity (MW)", "最大IT功率容量"), label("Maximum whole pods", "最大完整Pod数")]):
        ax.plot(p.pue, p[metric], color=COLORS[1], drawstyle="steps-post" if metric == "max_pods" else "default")
        ax.set(xlabel="PUE", title=title)
    save(fig, "pue_sensitivity")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.step(p.pue, p.total_gpus, where="post", color=COLORS[1])
    ax.set(xlabel="PUE", ylabel=label("GPU count", "GPU数量"), title=label("GPU capacity under the fixed facility budget", "固定设施功率预算下的GPU容量"))
    save(fig, "gpu_capacity_vs_pue")

    for name, x, heading in [("rack_density", "servers_per_rack", label("Servers per rack", "每机架服务器数")), ("pod_size", "racks_per_pod", label("Racks per pod", "每Pod机架数"))]:
        s = sweeps[name]
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.3))
        axes[0].plot(s[x], s.total_gpus, "o-", color=COLORS[1])
        axes[0].set(xlabel=heading, ylabel="GPU count", title=label("Maximum GPU deployment", "最大GPU部署数量"))
        axes[1].plot(s[x], s.remaining_capacity_mw, "o-", color=COLORS[2])
        axes[1].set(xlabel=heading, ylabel="Remaining MW", title=label("Unused facility capacity", "未使用的设施容量"))
        save(fig, name + "_sensitivity", label("One variable at a time; fixed network kW per rack. Physical fit is not validated.", "单因素扫描，机架网络功率固定；未验证物理安装条件。"))
