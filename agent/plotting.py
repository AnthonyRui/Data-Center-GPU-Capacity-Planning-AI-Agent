"""Single charts using the existing style. / 使用现有样式生成单张图表。"""

from src.plots import COLORS, configure_style


def render_plot(analysis_type, frame, path):
    """Render already verified model rows. / 绘制已验证的模型结果。"""
    import matplotlib.pyplot as plt

    chinese = configure_style()

    def label(en, zh):
        return en + "\n" + zh if chinese else en

    # Scoped rc_context disables Matplotlib math parsing for user-provided labels.
    # 局部关闭数学公式解析，将用户提供的标签作为普通文本显示。
    with plt.rc_context({"text.parse_math": False}):
        if analysis_type == "capacity":
            fig, axes = plt.subplots(1, 2, figsize=(11, 5))
            row = frame.iloc[0]
            bars = axes[0].bar(
                [
                    "Used / 已用" if chinese else "Used",
                    "Remaining / 剩余" if chinese else "Remaining",
                ],
                [row.used_capacity_mw, row.remaining_capacity_mw],
                color=COLORS[:2],
            )
            axes[0].bar_label(bars, fmt="%.3f", padding=4)
            axes[0].set(
                ylabel="MW", title=label("Facility power allocation", "设施功率分配")
            )
            axes[0].set_ylim(0, max(row.facility_capacity_mw, 1) * 1.15)
            axes[1].axis("off")
            axes[1].text(
                0.05,
                0.7,
                f"{int(row.max_pods):,} pods\n{int(row.total_racks):,} racks\n{int(row.total_gpus):,} GPUs",
                fontsize=17,
                linespacing=1.8,
            )
            axes[1].set_title(label("Complete-pod capacity", "完整 Pod 容量"))
            metrics = [
                "used_capacity_mw",
                "remaining_capacity_mw",
                "max_pods",
                "total_racks",
                "total_gpus",
            ]
        elif analysis_type == "comparison":
            # Horizontal labels support arbitrary names and more than three scenarios.
            # 横向标签支持自定义名称及超过三个场景。
            fig, axes = plt.subplots(1, 3, figsize=(15, max(5, len(frame) * 0.38 + 2)))
            metrics = ["pod_facility_power_mw", "max_pods", "total_gpus"]
            titles = [
                ("Facility MW / pod", "每 Pod 设施功率"),
                ("Whole pods", "完整 Pod 数"),
                ("GPU count", "GPU 数量"),
            ]
            for ax, metric, title in zip(axes, metrics, titles):
                bars = ax.barh(range(len(frame)), frame[metric], color=COLORS[1])
                ax.set_yticks(range(len(frame)), frame.scenario)
                ax.invert_yaxis()
                ax.bar_label(
                    bars,
                    labels=[
                        f"{v:,.3f}"
                        if metric == "pod_facility_power_mw"
                        else f"{v:,.0f}"
                        for v in frame[metric]
                    ],
                    padding=4,
                )
                ax.set_xlim(0, max(float(frame[metric].max()), 1) * 1.35)
                ax.set_title(label(*title))
        else:
            fig, axes = plt.subplots(1, 3, figsize=(14, 5))
            metrics = ["max_it_capacity_mw", "max_pods", "total_gpus"]
            titles = [
                ("Maximum IT capacity (MW)", "最大 IT 功率容量"),
                ("Whole pods", "完整 Pod 数"),
                ("GPU count", "GPU 数量"),
            ]
            for ax, metric, title in zip(axes, metrics, titles):
                ax.plot(
                    frame.pue,
                    frame[metric],
                    color=COLORS[1],
                    marker="o" if len(frame) == 1 else None,
                    drawstyle="default"
                    if metric == "max_it_capacity_mw"
                    else "steps-post",
                )
                ax.set(xlabel="PUE", title=label(*title))
        try:
            note = label(
                "Concept-level power estimate. Physical fit and electrical design are not validated.",
                "概念级功率估算，未验证物理安装条件或电气设计。",
            )
            fig.text(0.04, 0.025, note, fontsize=8, color="#56616a")
            fig.tight_layout(rect=(0, 0.11, 1, 1))
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation prevents accidental replacement. / 独占创建防止意外覆盖。
            with path.open("xb") as handle:
                fig.savefig(handle, format="png", dpi=180)
            return {
                "format": "png",
                "dpi": 180,
                "metrics": metrics,
                "labels_language": "en+zh" if chinese else "en",
                "caption_en": "Concept-level power capacity; computed results only.",
                "caption_zh": "概念级功率容量，仅绘制计算结果。",
            }
        finally:
            plt.close(fig)
