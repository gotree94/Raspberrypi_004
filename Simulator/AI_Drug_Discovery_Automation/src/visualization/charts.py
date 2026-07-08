"""
Charts and Plotting
====================
ADMET, 도킹, 분자 속성 분석 차트 생성.
matplotlib/seaborn 기반 시각화.
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import numpy as np

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Base Chart Generator
# ──────────────────────────────────────────────────────────


class ChartGenerator:
    """
    Base chart generator with save/show utilities.
    """

    def __init__(self, output_dir: Optional[str] = None, dpi: int = 150):
        cfg = get_config()
        self.output_dir = Path(output_dir or cfg.result_dir / "charts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        self._figures: List[Any] = []

    def save(self, filename: str, fig: Any, dpi: Optional[int] = None) -> str:
        """
        Save a figure to file.

        Args:
            filename: Output filename
            fig: Matplotlib figure
            dpi: Resolution

        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        fig.savefig(str(filepath), dpi=dpi or self.dpi, bbox_inches="tight")
        plt.close(fig)
        return str(filepath)

    def show(self, fig: Any) -> None:
        """Display a figure (if interactive)."""
        import matplotlib.pyplot as plt
        plt.show()
        plt.close(fig)


# ──────────────────────────────────────────────────────────
# ADMET Charts
# ──────────────────────────────────────────────────────────


class ADMETChart(ChartGenerator):
    """
    ADMET prediction visualization charts.
    """

    def plot_radar(self, predictions: Dict[str, Any], title: str = "ADMET Profile") -> Any:
        """
        Create a radar chart of ADMET properties.

        Args:
            predictions: ADMET prediction dictionary
            title: Chart title

        Returns:
            Matplotlib figure
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Filter numeric predictions
        categories = []
        values = []
        for key, value in predictions.items():
            if isinstance(value, (int, float)):
                categories.append(key)
                values.append(float(value))

        if not categories:
            return None

        # Normalize values to 0-1
        min_v, max_v = min(values), max(values)
        if max_v > min_v:
            norm_values = [(v - min_v) / (max_v - min_v) for v in values]
        else:
            norm_values = [0.5] * len(values)

        N = len(categories)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        values_normalized = norm_values + norm_values[:1]  # Close the polygon
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})

        ax.plot(angles, values_normalized, "o-", linewidth=2, color="#3498db")
        ax.fill(angles, values_normalized, alpha=0.25, color="#3498db")

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=9)

        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=7)

        ax.set_title(title, fontsize=12, fontweight="bold", pad=20)
        plt.tight_layout()
        return fig

    def plot_bar_comparison(
        self,
        ligands: List[str],
        predictions_list: List[Dict[str, float]],
        property_name: str = "aggregate_score",
        title: Optional[str] = None,
    ) -> Any:
        """
        Compare ADMET properties across multiple molecules.

        Args:
            ligands: List of ligand identifiers
            predictions_list: List of prediction dicts
            property_name: Property to compare
            title: Chart title

        Returns:
            Matplotlib figure
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        values = []
        for pred in predictions_list:
            if property_name in pred:
                val = pred[property_name]
            elif isinstance(pred, dict):
                val = pred.get(property_name, 0.0)
            else:
                val = 0.0
            values.append(float(val) if isinstance(val, (int, float)) else 0.0)

        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.arange(len(ligands))
        bars = ax.bar(x, values, color="#3498db", edgecolor="white", width=0.6)

        # Color bars by value
        for bar, val in zip(bars, values):
            if val >= 0.7:
                bar.set_color("#2ecc71")
            elif val >= 0.4:
                bar.set_color("#f39c12")
            else:
                bar.set_color("#e74c3c")

        ax.set_xticks(x)
        ax.set_xticklabels(ligands, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel(property_name, fontsize=10)
        ax.set_title(title or f"ADMET {property_name} Comparison", fontsize=11, fontweight="bold")

        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{val:.2f}", ha="center", va="bottom", fontsize=7)

        plt.tight_layout()
        return fig

    def plot_property_distribution(
        self,
        values: List[float],
        property_name: str = "Property",
        bins: int = 20,
    ) -> Any:
        """Plot distribution of a property across a library."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        # Histogram
        ax1.hist(values, bins=bins, color="#3498db", edgecolor="white", alpha=0.7)
        ax1.set_xlabel(property_name, fontsize=10)
        ax1.set_ylabel("Frequency", fontsize=10)
        ax1.set_title(f"{property_name} Distribution", fontsize=10)

        # Box plot
        ax2.boxplot(values, vert=True, patch_artist=True)
        ax2.set_ylabel(property_name, fontsize=10)
        ax2.set_title(f"{property_name} Summary", fontsize=10)
        ax2.set_xticks([])

        stats = {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }
        stats_text = "\n".join(f"{k}: {v:.2f}" for k, v in stats.items())
        ax2.text(1.3, 0.5, stats_text, transform=ax2.transAxes,
                 fontsize=8, verticalalignment="center",
                 bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

        plt.tight_layout()
        return fig

    def plot_lipinski_violations(
        self,
        mols_data: List[Dict[str, float]],
    ) -> Any:
        """Plot Lipinski rule violations for a set of molecules."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        properties = [
            ("MolWt", "Molecular Weight", 150, 500),
            ("MolLogP", "LogP", -2, 5),
            ("NumHDonors", "H-Bond Donors", 0, 5),
            ("NumHAcceptors", "H-Bond Acceptors", 0, 10),
        ]

        for ax, (key, label, low, high) in zip(axes.flatten(), properties):
            values = [m.get(key, 0) for m in mols_data]
            ax.scatter(range(len(values)), values, alpha=0.6, s=30)
            ax.axhline(y=low, color="green", linestyle="--", alpha=0.5, label=f"Lower: {low}")
            ax.axhline(y=high, color="red", linestyle="--", alpha=0.5, label=f"Upper: {high}")
            ax.set_xlabel("Molecule Index", fontsize=8)
            ax.set_ylabel(label, fontsize=8)
            ax.set_title(f"{label} Distribution", fontsize=9)
            ax.legend(fontsize=6)

        plt.tight_layout()
        return fig


# ──────────────────────────────────────────────────────────
# Docking Charts
# ──────────────────────────────────────────────────────────


class DockingChart(ChartGenerator):
    """
    Docking result visualization charts.
    """

    def plot_affinity_distribution(
        self,
        affinities: List[float],
        ligand_names: Optional[List[str]] = None,
        threshold: float = -8.0,
    ) -> Any:
        """
        Plot binding affinity distribution.

        Args:
            affinities: List of binding affinities (kcal/mol)
            ligand_names: Optional ligand names for labeling
            threshold: Hit threshold line

        Returns:
            Matplotlib figure
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Histogram
        ax1.hist(affinities, bins=15, color="#3498db", edgecolor="white", alpha=0.7)
        ax1.axvline(x=threshold, color="red", linestyle="--", label=f"Hit threshold: {threshold} kcal/mol")
        ax1.set_xlabel("Binding Affinity (kcal/mol)", fontsize=10)
        ax1.set_ylabel("Frequency", fontsize=10)
        ax1.set_title("Affinity Distribution", fontsize=11)
        ax1.legend(fontsize=8)

        hits = sum(1 for a in affinities if a <= threshold)
        ax1.text(0.95, 0.95, f"Hits: {hits}/{len(affinities)}",
                 transform=ax1.transAxes, ha="right", va="top",
                 bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.5))

        # Bar chart
        if ligand_names and len(ligand_names) == len(affinities):
            sorted_idx = np.argsort(affinities)
            sorted_names = [ligand_names[i] for i in sorted_idx]
            sorted_aff = [affinities[i] for i in sorted_idx]

            colors = ["#2ecc71" if a <= threshold else "#e74c3c" for a in sorted_aff]
            x = np.arange(len(sorted_names))
            ax2.bar(x, sorted_aff, color=colors, edgecolor="white", width=0.6)
            ax2.axhline(y=threshold, color="red", linestyle="--", alpha=0.7)
            ax2.set_xticks(x)
            ax2.set_xticklabels(sorted_names, rotation=45, ha="right", fontsize=7)
            ax2.set_ylabel("Binding Affinity (kcal/mol)", fontsize=10)
            ax2.set_title("Binding Affinities (sorted)", fontsize=11)
        else:
            ax2.scatter(range(len(affinities)), affinities, alpha=0.6, s=40, color="#3498db")
            ax2.axhline(y=threshold, color="red", linestyle="--")
            ax2.set_xlabel("Ligand Index", fontsize=10)
            ax2.set_ylabel("Binding Affinity (kcal/mol)", fontsize=10)
            ax2.set_title("Binding Affinities", fontsize=11)

        plt.tight_layout()
        return fig

    def plot_pose_rmsd(
        self,
        poses: List[Dict],
    ) -> Any:
        """
        Plot RMSD vs affinity for docking poses.

        Args:
            poses: List of pose dicts with 'affinity', 'rmsd_lower', 'rmsd_upper'

        Returns:
            Matplotlib figure
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        affinities = [p.get("affinity", 0) for p in poses]
        rmsds_lower = [p.get("rmsd_lower", 0) for p in poses]
        rmsds_upper = [p.get("rmsd_upper", 0) for p in poses]
        modes = [p.get("mode", i) for i, p in enumerate(poses)]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # RMSD lower vs affinity
        sc1 = ax1.scatter(rmsds_lower, affinities, c=modes, cmap="viridis", s=60, alpha=0.7)
        ax1.set_xlabel("RMSD Lower Bound (Å)", fontsize=10)
        ax1.set_ylabel("Binding Affinity (kcal/mol)", fontsize=10)
        ax1.set_title("RMSD vs Affinity", fontsize=11)
        plt.colorbar(sc1, ax=ax1, label="Pose Mode")

        # RMSD upper vs lower
        ax2.scatter(rmsds_lower, rmsds_upper, c=affinities, cmap="RdYlGn_r", s=60, alpha=0.7)
        ax2.set_xlabel("RMSD Lower Bound (Å)", fontsize=10)
        ax2.set_ylabel("RMSD Upper Bound (Å)", fontsize=10)
        ax2.set_title("RMSD Consistency", fontsize=11)

        # Diagonal line
        max_rmsd = max(max(rmsds_lower), max(rmsds_upper)) * 1.1
        ax2.plot([0, max_rmsd], [0, max_rmsd], "k--", alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_enrichment_curve(
        self,
        affinities: List[float],
        threshold: float = -8.0,
        label: str = "Docking",
    ) -> Any:
        """
        Plot enrichment curve (cumulative hit rate).

        Args:
            affinities: List of binding affinities sorted by rank
            threshold: Hit threshold
            label: Curve label

        Returns:
            Matplotlib figure
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sorted_aff = sorted(affinities)
        n_total = len(sorted_aff)
        n_hits_total = sum(1 for a in sorted_aff if a <= threshold)

        if n_hits_total == 0:
            return None

        # Cumulative hit count
        cumulative_hits = np.cumsum([1 for a in sorted_aff if a <= threshold])
        # Actually compute properly
        hit_mask = np.array([a <= threshold for a in sorted_aff])
        cumulative_hits = np.cumsum(hit_mask)
        fraction_screened = np.arange(1, n_total + 1) / n_total
        hit_rate = cumulative_hits / max(1, n_hits_total)

        fig, ax = plt.subplots(figsize=(8, 6))

        ax.plot(fraction_screened, hit_rate, linewidth=2, label=label)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.3, label="Random")

        ax.set_xlabel("Fraction Screened", fontsize=10)
        ax.set_ylabel("Fraction of Hits Found", fontsize=10)
        ax.set_title("Enrichment Curve", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        # EF at 1%, 5%, 10%
        ef_values = {}
        for frac in [0.01, 0.05, 0.10]:
            idx = max(1, int(n_total * frac))
            hits_at_frac = hit_mask[:idx].sum()
            ef = (hits_at_frac / idx) / (n_hits_total / n_total) if n_hits_total > 0 else 0
            ef_values[f"EF_{frac:.0%}"] = round(ef, 2)

        stats_text = "\n".join(f"{k}: {v}" for k, v in ef_values.items())
        ax.text(0.95, 0.1, stats_text, transform=ax.transAxes, fontsize=8,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

        plt.tight_layout()
        return fig

    def plot_top_hits(
        self,
        hits_data: List[Dict],
        top_n: int = 10,
    ) -> Any:
        """Plot top N docking hits."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sorted_hits = sorted(hits_data, key=lambda x: x.get("best_affinity", 0))[:top_n]

        names = [h.get("ligand_name", f"Hit {i}") for i, h in enumerate(sorted_hits)]
        affinities = [h.get("best_affinity", 0) for h in sorted_hits]

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.cm.RdYlGn_r(np.linspace(0.3, 0.9, len(sorted_hits)))

        bars = ax.barh(range(len(names)), affinities, color=colors, edgecolor="white")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("Binding Affinity (kcal/mol)", fontsize=10)
        ax.set_title(f"Top {min(top_n, len(sorted_hits))} Docking Hits", fontsize=11)

        # Add value labels
        for bar, aff in zip(bars, affinities):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{aff:.1f}", va="center", fontsize=8)

        ax.invert_yaxis()
        plt.tight_layout()
        return fig


# ──────────────────────────────────────────────────────────
# Analysis Charts (new)
# ──────────────────────────────────────────────────────────


class AnalysisChart(ChartGenerator):
    """
    General analysis charts for molecular properties and pipeline results.
    """

    def plot_correlation_matrix(
        self,
        property_dict: Dict[str, List[float]],
        title: str = "Property Correlation Matrix",
    ) -> Any:
        """Plot correlation matrix of molecular properties."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        names = list(property_dict.keys())
        values = np.array([property_dict[n] for n in names])

        corr_matrix = np.corrcoef(values)

        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(corr_matrix, cmap="RdBu_r", vmin=-1, vmax=1)

        ax.set_xticks(range(len(names)))
        ax.set_yticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(names, fontsize=8)

        # Add correlation values
        for i in range(len(names)):
            for j in range(len(names)):
                ax.text(j, i, f"{corr_matrix[i, j]:.2f}",
                        ha="center", va="center", fontsize=7)

        plt.colorbar(im, ax=ax, shrink=0.8)
        ax.set_title(title, fontsize=11)
        plt.tight_layout()
        return fig

    def plot_scatter_matrix(
        self,
        data: Dict[str, List[float]],
        color_by: Optional[List[float]] = None,
    ) -> Any:
        """Plot scatter matrix of properties."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        names = list(data.keys())
        n = len(names)

        fig, axes = plt.subplots(n, n, figsize=(4 * n, 4 * n))

        for i in range(n):
            for j in range(n):
                ax = axes[i, j]
                if i == j:
                    # Histogram on diagonal
                    ax.hist(data[names[i]], bins=15, color="#3498db", edgecolor="white")
                else:
                    if color_by is not None:
                        sc = ax.scatter(data[names[j]], data[names[i]],
                                        c=color_by, cmap="viridis", s=20, alpha=0.6)
                    else:
                        ax.scatter(data[names[j]], data[names[i]], s=20, alpha=0.6, color="#3498db")

                if i == n - 1:
                    ax.set_xlabel(names[j], fontsize=7)
                if j == 0:
                    ax.set_ylabel(names[i], fontsize=7)

        plt.suptitle("Property Scatter Matrix", fontsize=12)
        plt.tight_layout()
        return fig

    def plot_pipeline_timeline(
        self,
        stage_names: List[str],
        stage_durations: List[float],
        stage_statuses: List[str],
    ) -> Any:
        """Plot pipeline execution timeline (Gantt-style)."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))

        colors = {
            "completed": "#2ecc71",
            "running": "#3498db",
            "failed": "#e74c3c",
            "pending": "#95a5a6",
            "skipped": "#f39c12",
        }

        y_pos = np.arange(len(stage_names))
        start = 0

        for i, (name, duration, status) in enumerate(zip(stage_names, stage_durations, stage_statuses)):
            color = colors.get(status, "#95a5a6")
            ax.barh(i, duration, left=start, height=0.5, color=color, edgecolor="white")
            ax.text(start + duration + 0.5, i, f"{duration:.1f}s", va="center", fontsize=8)
            start += duration

        ax.set_yticks(y_pos)
        ax.set_yticklabels(stage_names, fontsize=9)
        ax.set_xlabel("Cumulative Time (seconds)", fontsize=10)
        ax.set_title("Pipeline Execution Timeline", fontsize=11, fontweight="bold")
        ax.invert_yaxis()

        plt.tight_layout()
        return fig


# Import for save/show parent class
import matplotlib
import matplotlib.pyplot as plt
