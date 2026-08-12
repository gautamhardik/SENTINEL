"""
Plotting and Visualization Utilities for Phase 6 Explainability.
Renders SHAP summaries, beeswarm plots, dependence plots, error distribution profiles, and confidence histograms.
"""
import matplotlib

matplotlib.use("Agg")
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid")


class ExplainabilityVisualizer:
    """Generates high-resolution visualization plots for model explainability, feature behavior, error profiling, and governance."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_global_shap_bar(self, df_imp: pl.DataFrame, top_n: int = 15, save_name: str = "shap_global_bar.png") -> Path:
        """Plots top N global SHAP feature importances."""
        df_pd = df_imp.head(top_n).to_pandas()
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        sns.barplot(data=df_pd, y="feature_name", x="mean_abs_shap", palette="mako", ax=ax)
        ax.set_xlabel("Mean Absolute SHAP Value (Impact on Model Output)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Feature Name", fontsize=10, fontweight="bold")
        ax.set_title(f"Top {top_n} Global Feature Impact (SHAP)", fontsize=12, fontweight="bold", pad=12)
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_cumulative_importance(self, df_imp: pl.DataFrame, save_name: str = "shap_cumulative_importance.png") -> Path:
        """Plots cumulative SHAP feature importance curve."""
        df_pd = df_imp.to_pandas()
        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        ax.plot(range(1, len(df_pd) + 1), df_pd["cumulative_pct"], marker="o", color="#1f77b4", linewidth=2)
        ax.axhline(y=90.0, color="red", linestyle="--", label="90% Variance Threshold")
        ax.set_xlabel("Number of Features Included", fontsize=10, fontweight="bold")
        ax.set_ylabel("Cumulative Importance (%)", fontsize=10, fontweight="bold")
        ax.set_title("Cumulative SHAP Feature Importance Curve", fontsize=12, fontweight="bold", pad=12)
        ax.legend(loc="lower right")
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_shap_beeswarm_custom(self, shap_values: np.ndarray, X: np.ndarray, feature_names: List[str], top_n: int = 15, save_name: str = "shap_beeswarm.png") -> Path:
        """Generates custom beeswarm plot showing feature value vs SHAP impact direction."""
        mean_abs = np.mean(np.abs(shap_values), axis=0)
        top_idx = np.argsort(mean_abs)[::-1][:top_n]

        fig, ax = plt.subplots(figsize=(9, 7), dpi=300)

        for pos, f_idx in enumerate(reversed(top_idx)):
            f_shap = shap_values[:, f_idx]
            f_val = X[:, f_idx]

            f_min, f_max = np.min(f_val), np.max(f_val)
            norm_val = (f_val - f_min) / (f_max - f_min + 1e-8)

            y_jitter = pos + np.random.normal(0, 0.08, size=len(f_shap))
            sc = ax.scatter(f_shap, y_jitter, c=norm_val, cmap="coolwarm", alpha=0.6, s=15, edgecolors="none")

        ax.set_yticks(range(top_n))
        ax.set_yticklabels([feature_names[i] for i in reversed(top_idx)], fontsize=9, fontweight="bold")
        ax.set_xlabel("SHAP Value (Impact on Fraud Probability)", fontsize=10, fontweight="bold")
        ax.set_title(f"Top {top_n} Feature SHAP Beeswarm Distribution", fontsize=12, fontweight="bold", pad=12)

        cbar = fig.colorbar(sc, ax=ax, orientation="vertical", shrink=0.7)
        cbar.set_label("Feature Value (Low = Blue, High = Red)", fontsize=9, fontweight="bold")
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_shap_dependence(self, feature_name: str, feature_idx: int, shap_values: np.ndarray, X: np.ndarray, save_name: str = "shap_dependence.png") -> Path:
        """Plots SHAP dependence scatter chart showing feature value vs SHAP contribution."""
        f_vals = X[:, feature_idx]
        s_vals = shap_values[:, feature_idx]

        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        sc = ax.scatter(f_vals, s_vals, c=s_vals, cmap="plasma", alpha=0.7, s=25, edgecolors="none")
        ax.axhline(y=0, color="gray", linestyle="--", linewidth=1)
        ax.set_xlabel(f"Feature Value ({feature_name})", fontsize=10, fontweight="bold")
        ax.set_ylabel("SHAP Impact on Fraud Risk", fontsize=10, fontweight="bold")
        ax.set_title(f"SHAP Dependence Plot — [{feature_name}]", fontsize=12, fontweight="bold", pad=12)
        fig.colorbar(sc, ax=ax, label="SHAP Value")
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_shap_waterfall_custom(self, sample_idx: int, X_row: np.ndarray, shap_row: np.ndarray, feature_names: List[str], proba: float, category: str, top_n: int = 8, save_name: str = "shap_waterfall.png") -> Path:
        """Plots local waterfall chart for a specific transaction."""
        top_idx = np.argsort(np.abs(shap_row))[::-1][:top_n]

        names = [feature_names[i] for i in reversed(top_idx)]
        values = [shap_row[i] for i in reversed(top_idx)]
        f_vals = [X_row[i] for i in reversed(top_idx)]

        labels = [f"{n} ({v:.2f})" for n, v in zip(names, f_vals)]
        colors = ["#d62728" if v > 0 else "#1f77b4" for v in values]

        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        ax.barh(labels, values, color=colors, height=0.6)
        ax.axvline(x=0, color="black", linestyle="--", linewidth=1)
        ax.set_xlabel("SHAP Contribution to Fraud Risk", fontsize=10, fontweight="bold")
        ax.set_title(f"Local SHAP Attribution — Sample #{sample_idx} [{category}] (Risk: {proba:.1%})", fontsize=11, fontweight="bold", pad=12)
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_confidence_histograms(self, y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.38, save_name: str = "error_confidence_histogram.png") -> Path:
        """Plots probability confidence distributions across TP, TN, FP, and FN error groups."""
        y_pred = (y_prob >= threshold).astype(int)

        tp_probs = y_prob[(y_true == 1) & (y_pred == 1)]
        tn_probs = y_prob[(y_true == 0) & (y_pred == 0)]
        fp_probs = y_prob[(y_true == 0) & (y_pred == 1)]
        fn_probs = y_prob[(y_true == 1) & (y_pred == 0)]

        fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
        ax.hist(tn_probs, bins=25, alpha=0.5, label=f"TN (Legit, n={len(tn_probs)})", color="green")
        ax.hist(tp_probs, bins=25, alpha=0.5, label=f"TP (Fraud, n={len(tp_probs)})", color="blue")
        ax.hist(fp_probs, bins=15, alpha=0.8, label=f"FP (False Alarm, n={len(fp_probs)})", color="orange")
        ax.hist(fn_probs, bins=15, alpha=0.8, label=f"FN (Missed Fraud, n={len(fn_probs)})", color="red")

        ax.axvline(x=threshold, color="black", linestyle=":", linewidth=2, label=f"Threshold ({threshold:.2f})")
        ax.set_xlabel("Calibrated Prediction Probability", fontsize=10, fontweight="bold")
        ax.set_ylabel("Transaction Count", fontsize=10, fontweight="bold")
        ax.set_title("Calibrated Probability Confidence Distributions across Error Groups", fontsize=12, fontweight="bold", pad=12)
        ax.legend(loc="upper center", frameon=True)
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_shap_stability(self, df_stab: pl.DataFrame, top_n: int = 15, save_name: str = "shap_stability.png") -> Path:
        """Plots SHAP feature ranking stability with std error bars across bootstrap samples."""
        df_pd = df_stab.head(top_n).to_pandas()
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        ax.errorbar(df_pd["mean_rank"], df_pd["feature_name"], xerr=df_pd["std_rank"], fmt="o", color="#1f77b4", ecolor="red", elinewidth=2, capsize=4)
        ax.invert_yaxis()
        ax.set_xlabel("Mean Importance Rank (1 = Highest)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Feature Name", fontsize=10, fontweight="bold")
        ax.set_title("SHAP Feature Importance Stability (Bootstrap n=10)", fontsize=12, fontweight="bold", pad=12)
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path

    def plot_robustness_heatmap(self, df_pert: pl.DataFrame, save_name: str = "robustness_heatmap.png") -> Path:
        """Plots heatmap matrix of probability shifts across multi-feature perturbations."""
        piv = df_pert.to_pandas().pivot(index="feature_name", columns="scale_factor", values="mean_abs_prob_shift")

        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        sns.heatmap(piv, annot=True, fmt=".4f", cmap="YlOrRd", ax=ax, cbar_kws={"label": "Mean Abs Probability Shift"})
        ax.set_title("Multi-Feature Sensitivity & Robustness Heatmap", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Perturbation Scale Factor", fontsize=10, fontweight="bold")
        ax.set_ylabel("Feature Name", fontsize=10, fontweight="bold")
        plt.tight_layout()

        path = self.output_dir / save_name
        plt.savefig(path)
        plt.close()
        return path
