"""
Pipeline Dashboard
===================
파이프라인 실행 모니터링 대시보드.
matplotlib 기반 실시간 상태 시각화.
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class DashboardPanel:
    """A panel in the dashboard layout."""
    title: str
    panel_type: str  # progress, chart, table, metrics
    data: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    size: Tuple[int, int] = (1, 1)


# ──────────────────────────────────────────────────────────
# Pipeline Dashboard
# ──────────────────────────────────────────────────────────


class PipelineDashboard:
    """
    Pipeline monitoring dashboard with multiple panels.

    Creates a comprehensive dashboard view of pipeline execution
    including progress bars, stage status, timing metrics, and charts.
    """

    def __init__(self, output_dir: Optional[str] = None):
        cfg = get_config()
        self.output_dir = Path(output_dir or cfg.result_dir / "dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.panels: List[DashboardPanel] = []
        self._dpi = 100

    def add_panel(self, panel: DashboardPanel) -> "PipelineDashboard":
        """Add a panel to the dashboard."""
        self.panels.append(panel)
        return self

    def create_stage_progress_chart(
        self,
        stage_names: List[str],
        stage_statuses: List[str],
        stage_times: Optional[List[float]] = None,
    ) -> DashboardPanel:
        """Create a stage progress bar chart."""
        data = {
            "stage_names": stage_names,
            "stage_statuses": stage_statuses,
            "stage_times": stage_times or [0.0] * len(stage_names),
        }
        return DashboardPanel(
            title="Stage Progress",
            panel_type="progress",
            data=data,
        )

    def create_metrics_panel(
        self,
        metrics: Dict[str, Any],
    ) -> DashboardPanel:
        """Create a metrics summary panel."""
        return DashboardPanel(
            title="Pipeline Metrics",
            panel_type="metrics",
            data={"metrics": metrics},
        )

    def render_dashboard(
        self,
        pipeline_id: str,
        panels: Optional[List[DashboardPanel]] = None,
        save: bool = True,
    ) -> Any:
        """
        Render the full dashboard.

        Args:
            pipeline_id: Pipeline identifier
            panels: List of panels (uses self.panels if None)
            save: Save to file

        Returns:
            Matplotlib figure
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        panels = panels or self.panels
        if not panels:
            return None

        # Determine grid layout
        n_panels = len(panels)
        n_cols = min(3, n_panels)
        n_rows = (n_panels + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 4 * n_rows))
        if n_panels == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        fig.suptitle(f"Pipeline Dashboard: {pipeline_id}", fontsize=14, fontweight="bold", y=0.98)

        STATUS_COLORS = {
            "completed": "#2ecc71",
            "running": "#3498db",
            "pending": "#95a5a6",
            "failed": "#e74c3c",
            "skipped": "#f39c12",
            "cancelled": "#9b59b6",
        }

        for i, panel in enumerate(panels):
            ax = axes[i]
            data = panel.data

            if panel.panel_type == "progress":
                self._render_progress_panel(ax, data, STATUS_COLORS)
            elif panel.panel_type == "metrics":
                self._render_metrics_panel(ax, data)
            elif panel.panel_type == "chart":
                ax.text(0.5, 0.5, f"Chart: {panel.title}", ha="center", va="center")
            elif panel.panel_type == "table":
                self._render_table_panel(ax, data)

            ax.set_title(panel.title, fontsize=10, fontweight="bold")

        # Hide unused axes
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.tight_layout()

        if save:
            filepath = self.output_dir / f"{pipeline_id}_dashboard.png"
            fig.savefig(str(filepath), dpi=self._dpi, bbox_inches="tight")
            plt.close(fig)
            return str(filepath)

        plt.close(fig)
        return fig

    def _render_progress_panel(self, ax, data: Dict, color_map: Dict) -> None:
        """Render a progress bar chart."""
        names = data.get("stage_names", [])
        statuses = data.get("stage_statuses", [])
        times = data.get("stage_times", [])

        if not names:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        y_pos = np.arange(len(names))
        colors = [color_map.get(s, "#95a5a6") for s in statuses]
        max_time = max(times) if times else 1

        # Horizontal bar chart
        bar_width = 0.6
        bars = ax.barh(y_pos, times, bar_width, color=colors, edgecolor="white")

        # Add status labels
        for i, (bar, status) in enumerate(zip(bars, statuses)):
            ax.text(
                bar.get_width() + max_time * 0.02,
                bar.get_y() + bar.get_height() / 2,
                status,
                va="center",
                fontsize=8,
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("Runtime (seconds)", fontsize=8)
        ax.invert_yaxis()

        # Legend
        legend_patches = [
            mpatches.Patch(color=color, label=status)
            for status, color in color_map.items()
            if status in statuses
        ]
        if legend_patches:
            ax.legend(handles=legend_patches, fontsize=6, loc="lower right")

    def _render_metrics_panel(self, ax, data: Dict) -> None:
        """Render a metrics summary panel."""
        metrics = data.get("metrics", {})
        if not metrics:
            ax.text(0.5, 0.5, "No metrics", ha="center", va="center")
            return

        ax.axis("off")
        y = 0.9
        for key, value in metrics.items():
            if isinstance(value, float):
                text = f"{key}: {value:.2f}"
            else:
                text = f"{key}: {value}"
            ax.text(0.1, y, text, fontsize=9, transform=ax.transAxes)
            y -= 0.12

    def _render_table_panel(self, ax, data: Dict) -> None:
        """Render a table panel."""
        headers = data.get("headers", [])
        rows = data.get("rows", [])

        if not rows:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        ax.axis("off")
        table = ax.table(
            cellText=rows,
            colLabels=headers,
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)

    def render_pipeline_summary(
        self,
        stages: List[Dict],
        metrics: Dict[str, Any],
        title: str = "Pipeline Summary",
    ) -> Any:
        """Render a single summary chart for the pipeline."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle(title, fontsize=12, fontweight="bold")

        # Left: Stage status pie chart
        statuses = [s.get("status", "unknown") for s in stages]
        status_counts = {}
        for s in statuses:
            status_counts[s] = status_counts.get(s, 0) + 1

        colors = {
            "completed": "#2ecc71",
            "running": "#3498db",
            "pending": "#95a5a6",
            "failed": "#e74c3c",
            "skipped": "#f39c12",
        }
        pie_colors = [colors.get(k, "#95a5a6") for k in status_counts.keys()]

        ax1.pie(
            status_counts.values(),
            labels=status_counts.keys(),
            colors=pie_colors,
            autopct="%1.1f%%",
            startangle=90,
        )
        ax1.set_title("Stage Status Distribution")

        # Right: Metrics text
        ax2.axis("off")
        y = 0.9
        for key, value in metrics.items():
            if isinstance(value, float):
                text = f"{key}: {value:.2f}"
            else:
                text = f"{key}: {value}"
            ax2.text(0.1, y, text, fontsize=10, transform=ax2.transAxes)
            y -= 0.08

        plt.tight_layout()
        return fig

    def animate_progress(
        self,
        pipeline_id: str,
        num_frames: int = 20,
    ) -> Optional[str]:
        """
        Create an animated GIF of pipeline progress.

        Requires matplotlib.animation.

        Args:
            pipeline_id: Pipeline identifier
            num_frames: Number of frames in the animation

        Returns:
            Path to GIF file, or None if animation failed
        """
        try:
            import matplotlib.animation as animation
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        fig, ax = plt.subplots(figsize=(8, 6))

        def update(frame):
            ax.clear()
            progress = (frame + 1) / num_frames
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.barh(0, progress, height=0.3, color="#3498db")
            ax.set_yticks([])
            ax.set_title(f"Pipeline: {pipeline_id} ({progress:.0%})")
            ax.text(progress + 0.02, 0, f"{progress:.0%}", va="center", fontsize=12)

        anim = animation.FuncAnimation(fig, update, frames=num_frames, interval=200)
        gif_path = str(self.output_dir / f"{pipeline_id}_progress.gif")
        anim.save(gif_path, writer="pillow")
        plt.close(fig)
        return gif_path
