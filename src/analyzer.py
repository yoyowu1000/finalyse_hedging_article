"""Analysis and visualization tools for hedging results."""

from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from .models import Bond, Liability, YieldCurve
from .optimizer import calculate_bond_cashflows, calculate_present_value

# Set style for better-looking plots
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")


class HedgingAnalyzer:
    """Analyzes and visualizes hedging results."""

    def __init__(
        self,
        liabilities: list[Liability],
        bonds: list[Bond],
        quantities: np.ndarray,
        yield_curve: YieldCurve,
    ):
        """Initialize analyzer with hedging solution.

        Args:
            liabilities: List of liability cashflows
            bonds: List of bonds in portfolio
            quantities: Optimal quantities of each bond
            yield_curve: Current yield curve
        """
        self.liabilities = liabilities
        self.bonds = bonds
        self.quantities = quantities
        self.yield_curve = yield_curve

    def create_cashflow_comparison(self, save_path: Optional[str] = None) -> plt.Figure:
        """Create detailed cashflow comparison chart.

        Args:
            save_path: Optional path to save the figure

        Returns:
            Matplotlib figure object
        """
        # Get all relevant time points
        all_times = set()
        for liability in self.liabilities:
            all_times.add(liability.time_years)

        for bond, qty in zip(self.bonds, self.quantities):
            if qty > 0.01:
                for time, _ in calculate_bond_cashflows(bond):
                    all_times.add(time)

        all_times = sorted(all_times)

        # Calculate cashflows
        liability_cfs = []
        asset_cfs = []

        for t in all_times:
            # Liability cashflow
            liability_cf = sum(
                liability.amount for liability in self.liabilities if abs(liability.time_years - t) < 0.001
            )
            liability_cfs.append(liability_cf)

            # Asset cashflow
            asset_cf = 0
            for bond, qty in zip(self.bonds, self.quantities):
                bond_cf = sum(
                    cf
                    for time, cf in calculate_bond_cashflows(bond)
                    if abs(time - t) < 0.001
                )
                asset_cf += bond_cf * qty
            asset_cfs.append(asset_cf)

        # Create visualization
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Cashflow comparison
        x = np.arange(len(all_times))
        width = 0.35

        bars1 = ax1.bar(
            x - width / 2,
            liability_cfs,
            width,
            label="Liabilities",
            alpha=0.8,
            color="#e74c3c",
        )
        bars2 = ax1.bar(
            x + width / 2,
            asset_cfs,
            width,
            label="Hedging Portfolio",
            alpha=0.8,
            color="#3498db",
        )

        ax1.set_xlabel("Time (Years)", fontsize=12)
        ax1.set_ylabel("Cash Flow ($)", fontsize=12)
        ax1.set_title("Liability vs Asset Cash Flows", fontsize=14, fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"{t:.1f}" for t in all_times])
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax1.annotate(
                        f"${height:,.0f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )

        # Mismatch analysis
        mismatches = [
            asset - liability for asset, liability in zip(asset_cfs, liability_cfs)
        ]
        colors = ["#27ae60" if m >= 0 else "#e74c3c" for m in mismatches]

        bars3 = ax2.bar(x, mismatches, color=colors, alpha=0.8)
        ax2.set_xlabel("Time (Years)", fontsize=12)
        ax2.set_ylabel("Cash Flow Mismatch ($)", fontsize=12)
        ax2.set_title(
            "Hedging Effectiveness: Cash Flow Mismatches",
            fontsize=14,
            fontweight="bold",
        )
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"{t:.1f}" for t in all_times])
        ax2.axhline(y=0, color="black", linestyle="-", linewidth=1)
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        # Add value labels
        for bar in bars3:
            height = bar.get_height()
            if abs(height) > 0:
                ax2.annotate(
                    f"${height:,.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3 if height > 0 else -15),
                    textcoords="offset points",
                    ha="center",
                    va="bottom" if height > 0 else "top",
                    fontsize=9,
                )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig

    def sensitivity_analysis(
        self,
        yield_shifts: np.ndarray = np.linspace(-0.02, 0.02, 9),
        save_path: Optional[str] = None,
    ) -> Tuple[plt.Figure, dict]:
        """Perform sensitivity analysis for parallel yield curve shifts.

        Args:
            yield_shifts: Array of yield shifts to test
            save_path: Optional path to save the figure

        Returns:
            Tuple of (figure, results_dict)
        """
        # Base case values
        base_liability_pv = sum(
            liability.amount * self.yield_curve.get_discount_factor(liability.time_years)
            for liability in self.liabilities
        )

        base_asset_pv = sum(
            qty
            * calculate_present_value(calculate_bond_cashflows(bond), self.yield_curve)
            for bond, qty in zip(self.bonds, self.quantities)
        )

        # Calculate sensitivities
        liability_pvs = []
        asset_pvs = []
        hedge_ratios = []
        tracking_errors = []

        for shift in yield_shifts:
            # Create shifted yield curve
            shifted_curve = self.yield_curve.shift_parallel(shift)

            # Calculate new PVs
            liability_pv = sum(
                liability.amount * shifted_curve.get_discount_factor(liability.time_years)
                for liability in self.liabilities
            )

            asset_pv = sum(
                qty
                * calculate_present_value(calculate_bond_cashflows(bond), shifted_curve)
                for bond, qty in zip(self.bonds, self.quantities)
            )

            liability_pvs.append(liability_pv)
            asset_pvs.append(asset_pv)

            # Calculate metrics
            if base_liability_pv != 0:
                hedge_ratio = asset_pv / liability_pv if liability_pv != 0 else 1.0
                hedge_ratios.append(hedge_ratio)

                liability_change = (
                    liability_pv - base_liability_pv
                ) / base_liability_pv
                asset_change = (asset_pv - base_asset_pv) / base_asset_pv
                tracking_error = asset_change - liability_change
                tracking_errors.append(tracking_error)
            else:
                hedge_ratios.append(1.0)
                tracking_errors.append(0.0)

        # Create visualization
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # PV changes
        ax1.plot(
            yield_shifts * 100,
            (np.array(liability_pvs) / base_liability_pv - 1) * 100,
            "r-",
            label="Liabilities",
            linewidth=2.5,
            marker="o",
        )
        ax1.plot(
            yield_shifts * 100,
            (np.array(asset_pvs) / base_asset_pv - 1) * 100,
            "b-",
            label="Hedging Portfolio",
            linewidth=2.5,
            marker="s",
        )
        ax1.set_xlabel("Yield Shift (basis points)", fontsize=12)
        ax1.set_ylabel("PV Change (%)", fontsize=12)
        ax1.set_title(
            "Interest Rate Sensitivity Analysis", fontsize=14, fontweight="bold"
        )
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        ax1.axvline(x=0, color="black", linestyle="--", alpha=0.5)

        # Hedge ratios
        ax2.plot(yield_shifts * 100, hedge_ratios, "g-", linewidth=2.5, marker="D")
        ax2.axhline(y=1.0, color="black", linestyle="--", alpha=0.5)
        ax2.set_xlabel("Yield Shift (basis points)", fontsize=12)
        ax2.set_ylabel("Hedge Ratio", fontsize=12)
        ax2.set_title("Hedge Ratio Stability", fontsize=14, fontweight="bold")
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([0.95, 1.05])

        # Tracking error
        ax3.plot(
            yield_shifts * 100,
            np.array(tracking_errors) * 100,
            "purple",
            linewidth=2.5,
            marker="^",
        )
        ax3.set_xlabel("Yield Shift (basis points)", fontsize=12)
        ax3.set_ylabel("Tracking Error (%)", fontsize=12)
        ax3.set_title("Tracking Error Analysis", fontsize=14, fontweight="bold")
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        ax3.axvline(x=0, color="black", linestyle="--", alpha=0.5)

        # Summary statistics
        ax4.axis("off")
        summary_text = f"""Hedging Performance Summary:
        
Base Liability PV: ${base_liability_pv:,.0f}
Base Asset PV: ${base_asset_pv:,.0f}
Initial Hedge Ratio: {base_asset_pv / base_liability_pv:.4f}

Tracking Error Statistics:
Max Absolute Error: {max(abs(e) for e in tracking_errors) * 100:.2f}%
Mean Absolute Error: {np.mean([abs(e) for e in tracking_errors]) * 100:.2f}%
Standard Deviation: {np.std(tracking_errors) * 100:.2f}%

Hedge Effectiveness:
Risk Reduction: {(1 - np.std(tracking_errors) / np.std([(pv / base_liability_pv - 1) for pv in liability_pvs])) * 100:.1f}%
"""
        ax4.text(
            0.1,
            0.9,
            summary_text,
            transform=ax4.transAxes,
            fontsize=12,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig, {
            "yield_shifts": yield_shifts.tolist(),
            "liability_pvs": liability_pvs,
            "asset_pvs": asset_pvs,
            "hedge_ratios": hedge_ratios,
            "tracking_errors": tracking_errors,
        }
