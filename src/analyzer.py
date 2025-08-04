"""Analysis and visualization tools for hedging results."""

from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from .models import Bond, Liability, YieldCurve
from .optimizer import (
    calculate_bond_present_value,
    calculate_duration,
)

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
            liability.amount
            * self.yield_curve.get_discount_factor(liability.time_years)
            for liability in self.liabilities
        )

        base_asset_pv = sum(
            qty * calculate_bond_present_value(bond, self.yield_curve)
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
                liability.amount
                * shifted_curve.get_discount_factor(liability.time_years)
                for liability in self.liabilities
            )

            asset_pv = sum(
                qty * calculate_bond_present_value(bond, shifted_curve)
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
        
Base Liability PV: €{base_liability_pv:,.0f}k
Base Asset PV: €{base_asset_pv:,.0f}k
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

    def create_portfolio_comparison(
        self,
        initial_quantities: np.ndarray,
        optimized_quantities: np.ndarray,
        optimization_type: str = "Duration Matching",
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """Create visualization comparing initial and optimized portfolios.

        Args:
            initial_quantities: Initial portfolio quantities
            optimized_quantities: Optimized portfolio quantities
            optimization_type: Type of optimization performed
            save_path: Optional path to save the figure

        Returns:
            Matplotlib figure object
        """

        # Calculate metrics for both portfolios
        def calculate_metrics(quantities):
            portfolio_pv = sum(
                qty * calculate_bond_present_value(bond, self.yield_curve)
                for bond, qty in zip(self.bonds, quantities)
            )

            portfolio_duration = 0
            if portfolio_pv > 0:
                for bond, qty in zip(self.bonds, quantities):
                    if qty > 0:
                        bond_pv = calculate_bond_present_value(bond, self.yield_curve)
                        bond_duration = calculate_duration(bond, self.yield_curve)
                        portfolio_duration += (
                            qty * bond_pv * bond_duration
                        ) / portfolio_pv

            return portfolio_pv, portfolio_duration

        # Calculate liability metrics
        liability_pv = sum(
            liability.amount
            * self.yield_curve.get_discount_factor(liability.time_years)
            for liability in self.liabilities
        )

        liability_duration = (
            sum(
                liability.amount
                * liability.time_years
                * self.yield_curve.get_discount_factor(liability.time_years)
                for liability in self.liabilities
            )
            / liability_pv
        )

        # Calculate portfolio metrics
        initial_pv, initial_duration = calculate_metrics(initial_quantities)
        optimized_pv, optimized_duration = calculate_metrics(optimized_quantities)

        # Create figure with subplots
        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], hspace=0.3, wspace=0.3)

        # 1. Bond allocation comparison
        ax1 = fig.add_subplot(gs[0, :])
        bond_labels = [
            f"{bond.maturity_years}Y {bond.coupon_rate:.1%}" for bond in self.bonds
        ]
        x = np.arange(len(self.bonds))
        width = 0.35

        bars1 = ax1.bar(
            x - width / 2,
            initial_quantities,
            width,
            label="Initial Portfolio",
            alpha=0.8,
            color="#ff7f0e",
        )
        bars2 = ax1.bar(
            x + width / 2,
            optimized_quantities,
            width,
            label="Optimized Portfolio",
            alpha=0.8,
            color="#2ca02c",
        )

        ax1.set_xlabel("Bonds", fontsize=12)
        ax1.set_ylabel("Quantity", fontsize=12)
        ax1.set_title("Bond Allocation Comparison", fontsize=14, fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels(bond_labels, rotation=45, ha="right")
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0.1:
                    ax1.annotate(
                        f"{height:.0f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

        # 2. Liability Cashflow Profile
        ax2 = fig.add_subplot(gs[1, :])
        
        # Group liabilities by time
        liability_times = {}
        for liability in self.liabilities:
            if liability.time_years not in liability_times:
                liability_times[liability.time_years] = 0
            liability_times[liability.time_years] += liability.amount
        
        # Calculate cashflows for both portfolios
        initial_cashflows = calculate_bond_cashflows(initial_quantities)
        optimized_cashflows = calculate_bond_cashflows(optimized_quantities)
        
        # Get all unique times
        all_times = sorted(set(list(liability_times.keys()) + 
                             list(initial_cashflows.keys()) + 
                             list(optimized_cashflows.keys())))
        
        # Prepare data for plotting
        liability_amounts = [liability_times.get(t, 0) for t in all_times]
        initial_amounts = [initial_cashflows.get(t, 0) for t in all_times]
        optimized_amounts = [optimized_cashflows.get(t, 0) for t in all_times]
        
        # Plot grouped bars
        x = np.arange(len(all_times))
        width = 0.25
        
        bars1 = ax2.bar(x - width, liability_amounts, width, 
                        label="Liabilities", alpha=0.8, color="#e74c3c")
        bars2 = ax2.bar(x, initial_amounts, width, 
                        label="Initial Portfolio", alpha=0.8, color="#ff7f0e")
        bars3 = ax2.bar(x + width, optimized_amounts, width, 
                        label="Optimized Portfolio", alpha=0.8, color="#2ca02c")
        
        ax2.set_xlabel("Time (Years)", fontsize=12)
        ax2.set_ylabel("Cash Flow Amount (€)", fontsize=12)
        ax2.set_title("Cash Flow Profiles Comparison", fontsize=14, fontweight="bold")
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"{t:.0f}" for t in all_times])
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # Add value labels on significant bars only
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                if height > 100000:  # Only label significant cashflows
                    ax2.annotate(
                        f"€{height/1000:.0f}k",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        rotation=90 if height > 3000000 else 0
                    )

        # 3. Key metrics comparison
        ax3 = fig.add_subplot(gs[2, 0])
        metrics = ["Present Value", "Duration"]
        initial_values = [initial_pv, initial_duration]
        optimized_values = [optimized_pv, optimized_duration]
        target_values = [liability_pv, liability_duration]

        x = np.arange(len(metrics))
        width = 0.25

        ax3.bar(
            x - width,
            initial_values,
            width,
            label="Initial",
            alpha=0.8,
            color="#ff7f0e",
        )
        ax3.bar(
            x, optimized_values, width, label="Optimized", alpha=0.8, color="#2ca02c"
        )
        ax3.bar(
            x + width,
            target_values,
            width,
            label="Target (Liability)",
            alpha=0.8,
            color="#e74c3c",
        )

        ax3.set_ylabel("Value", fontsize=12)
        ax3.set_title("Portfolio Metrics Comparison", fontsize=14, fontweight="bold")
        ax3.set_xticks(x)
        ax3.set_xticklabels(metrics)
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)

        # 4. Tracking error improvement
        ax4 = fig.add_subplot(gs[2, 1])

        # Calculate tracking errors
        initial_pv_error = abs(initial_pv - liability_pv) / liability_pv * 100
        optimized_pv_error = abs(optimized_pv - liability_pv) / liability_pv * 100
        initial_duration_error = abs(initial_duration - liability_duration)
        optimized_duration_error = abs(optimized_duration - liability_duration)

        error_types = ["PV Error (%)", "Duration Error (years)"]
        initial_errors = [initial_pv_error, initial_duration_error]
        optimized_errors = [optimized_pv_error, optimized_duration_error]

        x = np.arange(len(error_types))
        width = 0.35

        ax4.bar(
            x - width / 2,
            initial_errors,
            width,
            label="Initial",
            alpha=0.8,
            color="#ff7f0e",
        )
        ax4.bar(
            x + width / 2,
            optimized_errors,
            width,
            label="Optimized",
            alpha=0.8,
            color="#2ca02c",
        )

        ax4.set_ylabel("Error", fontsize=12)
        ax4.set_title("Tracking Error Comparison", fontsize=14, fontweight="bold")
        ax4.set_xticks(x)
        ax4.set_xticklabels(error_types)
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)

        # Add improvement percentages (excluding 100% improvements)
        for i, (initial, optimized) in enumerate(zip(initial_errors, optimized_errors)):
            if initial > 0 and optimized > 0.001:  # Avoid showing 100% improvement
                improvement = (initial - optimized) / initial * 100
                ax4.text(
                    i,
                    max(initial, optimized) * 1.1,
                    f"{improvement:.0f}% improvement",
                    ha="center",
                    fontsize=10,
                    color="green" if improvement > 0 else "red",
                )

        plt.suptitle(
            f"Portfolio Optimization Analysis: {optimization_type}",
            fontsize=16,
            fontweight="bold",
        )

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig
