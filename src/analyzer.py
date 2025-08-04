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
        # Import convexity calculation
        from .optimizer import calculate_convexity

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

        # Calculate base convexities
        base_asset_convexity = sum(
            qty
            * calculate_convexity(bond, self.yield_curve)
            * calculate_bond_present_value(bond, self.yield_curve)
            / base_asset_pv
            for bond, qty in zip(self.bonds, self.quantities)
            if qty > 0
        )

        # Liability convexity (simplified calculation)
        base_liability_convexity = sum(
            liability.amount
            * (liability.time_years**2 + liability.time_years)
            * self.yield_curve.get_discount_factor(liability.time_years)
            / base_liability_pv
            for liability in self.liabilities
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

        # Add explanatory text for tracking error
        ax3.text(
            0.02,
            0.98,
            "Tracking Error = Asset PV% Change - Liability PV% Change\n"
            + "(0% = perfect hedge, ±% = hedge mismatch)",
            transform=ax3.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7),
        )

        # Convexity Analysis
        ax4.set_title("Convexity Analysis", fontsize=14, fontweight="bold")

        # Calculate convexity effect for each yield shift
        convexity_effects = []
        for shift in yield_shifts:
            # Approximate PV change using duration and convexity
            # ΔPV/PV ≈ -Duration × Δy + 0.5 × Convexity × (Δy)²
            liability_convexity_effect = (
                0.5 * base_liability_convexity * (shift**2) * 100
            )
            asset_convexity_effect = 0.5 * base_asset_convexity * (shift**2) * 100

            # Net convexity effect (positive means assets benefit more from convexity)
            net_convexity_effect = asset_convexity_effect - liability_convexity_effect
            convexity_effects.append(net_convexity_effect)

        # Plot convexity effects
        ax4.plot(
            yield_shifts * 100, convexity_effects, "orange", linewidth=2.5, marker="D"
        )
        ax4.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        ax4.axvline(x=0, color="black", linestyle="--", alpha=0.5)
        ax4.set_xlabel("Yield Shift (basis points)", fontsize=12)
        ax4.set_ylabel("Convexity Benefit (%)", fontsize=12)
        ax4.grid(True, alpha=0.3)

        # Add convexity values and explanation
        convexity_text = (
            f"Asset Convexity: {base_asset_convexity:.1f}\n"
            + f"Liability Convexity: {base_liability_convexity:.1f}\n"
            + f"Convexity Mismatch: {base_asset_convexity - base_liability_convexity:.1f}"
        )

        ax4.text(
            0.02,
            0.98,
            convexity_text,
            transform=ax4.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.7),
        )

        # Add explanation for convexity
        if base_asset_convexity > base_liability_convexity:
            explanation = "Higher asset convexity provides\nadditional protection in volatile markets"
        else:
            explanation = "Lower asset convexity may\nunderperform in volatile markets"

        ax4.text(
            0.98,
            0.02,
            explanation,
            transform=ax4.transAxes,
            fontsize=8,
            verticalalignment="bottom",
            horizontalalignment="right",
            style="italic",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="lightgreen"
                if base_asset_convexity > base_liability_convexity
                else "lightcoral",
                alpha=0.5,
            ),
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
            "asset_convexity": base_asset_convexity,
            "liability_convexity": base_liability_convexity,
            "convexity_effects": convexity_effects,
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
        fig = plt.figure(figsize=(18, 14))
        gs = fig.add_gridspec(3, 2, height_ratios=[1, 1.2, 1], hspace=0.5, wspace=0.3)

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

        ax1.set_xlabel("Bonds", fontsize=12, labelpad=10)
        ax1.set_ylabel("Quantity", fontsize=12)
        ax1.set_title(
            "Bond Allocation Comparison", fontsize=14, fontweight="bold", pad=20
        )
        ax1.set_xticks(x)
        ax1.set_xticklabels(bond_labels, rotation=45, ha="right")
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)

        # Add extra bottom margin for rotated labels
        ax1.margins(y=0.1)

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

        # 2. Cash Flow Profiles Comparison
        ax2 = fig.add_subplot(gs[1, :])

        # Calculate bond cashflows for both portfolios
        def calculate_bond_cashflows(quantities):
            cashflow_times = {}
            for bond, qty in zip(self.bonds, quantities):
                if qty > 0:
                    # Annual coupon payments
                    for year in range(1, int(bond.maturity_years) + 1):
                        time = float(year)
                        if time not in cashflow_times:
                            cashflow_times[time] = 0
                        cashflow_times[time] += qty * bond.face_value * bond.coupon_rate

                    # Principal repayment at maturity
                    if bond.maturity_years not in cashflow_times:
                        cashflow_times[bond.maturity_years] = 0
                    cashflow_times[bond.maturity_years] += qty * bond.face_value
            return cashflow_times

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
        all_times = sorted(
            set(
                list(liability_times.keys())
                + list(initial_cashflows.keys())
                + list(optimized_cashflows.keys())
            )
        )

        # Prepare data for plotting
        liability_amounts = [liability_times.get(t, 0) for t in all_times]
        initial_amounts = [initial_cashflows.get(t, 0) for t in all_times]
        optimized_amounts = [optimized_cashflows.get(t, 0) for t in all_times]

        # Plot grouped bars
        x = np.arange(len(all_times))
        width = 0.25

        bars1 = ax2.bar(
            x - width,
            liability_amounts,
            width,
            label="Liabilities",
            alpha=0.8,
            color="#e74c3c",
        )
        bars2 = ax2.bar(
            x,
            initial_amounts,
            width,
            label="Initial Portfolio",
            alpha=0.8,
            color="#ff7f0e",
        )
        bars3 = ax2.bar(
            x + width,
            optimized_amounts,
            width,
            label="Optimized Portfolio",
            alpha=0.8,
            color="#2ca02c",
        )

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
                        f"€{height / 1000:.0f}k",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        rotation=90 if height > 3000000 else 0,
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
