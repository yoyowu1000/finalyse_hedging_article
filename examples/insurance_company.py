"""Real-world insurance company hedging example."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.models import Liability, Bond, YieldCurve
from src.optimizer import HedgingOptimizer
from src.analyzer import HedgingAnalyzer
import numpy as np


def create_insurance_liabilities():
    """Create realistic insurance liability profile."""
    # Mix of different insurance products
    liabilities = [
        # Short-term death benefits
        Liability(time_years=0.5, amount=500_000),
        Liability(time_years=1, amount=1_000_000),
        Liability(time_years=1.5, amount=750_000),
        # Medium-term annuity payments
        Liability(time_years=3, amount=2_500_000),
        Liability(time_years=4, amount=2_200_000),
        Liability(time_years=5, amount=1_800_000),
        # Long-term endowments and pensions
        Liability(time_years=7, amount=3_000_000),
        Liability(time_years=10, amount=3_200_000),
        Liability(time_years=15, amount=4_500_000),
        Liability(time_years=20, amount=5_000_000),
    ]
    return liabilities


def create_bond_universe():
    """Create available bonds for investment."""
    # Government and corporate bonds with various maturities
    bonds = [
        # Short-term bonds
        Bond(maturity_years=1, coupon_rate=0.020, face_value=1000),
        Bond(maturity_years=2, coupon_rate=0.025, face_value=1000),
        # Medium-term bonds
        Bond(maturity_years=3, coupon_rate=0.028, face_value=1000),
        Bond(maturity_years=5, coupon_rate=0.032, face_value=1000),
        Bond(maturity_years=7, coupon_rate=0.035, face_value=1000),
        # Long-term bonds
        Bond(maturity_years=10, coupon_rate=0.038, face_value=1000),
        Bond(maturity_years=15, coupon_rate=0.042, face_value=1000),
        Bond(maturity_years=20, coupon_rate=0.045, face_value=1000),
    ]
    return bonds


def create_yield_curve():
    """Create current market yield curve."""
    # Upward sloping yield curve
    return YieldCurve(
        times=[0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30],
        rates=[0.018, 0.020, 0.025, 0.028, 0.032, 0.035, 0.038, 0.042, 0.045, 0.048],
    )


def main():
    """Run comprehensive insurance company hedging analysis."""

    print("=== Insurance Company Liability Hedging Analysis ===\n")

    # Create market data
    liabilities = create_insurance_liabilities()
    bonds = create_bond_universe()
    yield_curve = create_yield_curve()

    # Calculate total liability value
    total_liability = sum(liability.amount for liability in liabilities)
    print(f"Total Liability Amount: ${total_liability:,.0f}")
    print(f"Number of Liability Payments: {len(liabilities)}")
    print(f"Time Horizon: {max(liability.time_years for liability in liabilities)} years\n")

    # Run both optimization strategies
    optimizer = HedgingOptimizer(liabilities, bonds, yield_curve)

    # Duration matching
    print("1. Duration Matching Strategy")
    print("-" * 40)
    duration_result = optimizer.duration_matching()

    if duration_result["success"]:
        print("✓ Optimization successful")
        print(f"  Liability PV: ${duration_result['liability_pv']:,.0f}")
        print(
            f"  Liability Duration: {duration_result['liability_duration']:.2f} years"
        )
        print(f"  Portfolio PV: ${duration_result['portfolio_pv']:,.0f}")
        print(
            f"  Portfolio Duration: {duration_result['portfolio_duration']:.2f} years"
        )
        print(
            f"  PV Matching Error: {abs(duration_result['portfolio_pv'] - duration_result['liability_pv']) / duration_result['liability_pv'] * 100:.2f}%"
        )
        print(
            f"  Duration Matching Error: {abs(duration_result['portfolio_duration'] - duration_result['liability_duration']):.3f} years"
        )

        print("\n  Bond Allocations:")
        total_invested = 0
        for bond, qty in duration_result["bond_allocations"]:
            value = qty * bond.face_value
            total_invested += value
            print(f"  - {bond}: {qty:,.0f} units (${value:,.0f})")
        print(f"  Total Investment Required: ${total_invested:,.0f}")
    else:
        print("✗ Duration matching optimization failed")

    # Cash flow matching
    print("\n2. Cash Flow Matching Strategy")
    print("-" * 40)
    cashflow_result = optimizer.cash_flow_matching()

    if cashflow_result["success"]:
        print("✓ Optimization successful")
        print(f"  Total Cost: ${cashflow_result['total_cost']:,.0f}")

        print("\n  Bond Allocations:")
        total_invested = 0
        for bond, qty in cashflow_result["bond_allocations"]:
            value = qty * bond.face_value
            total_invested += value
            print(f"  - {bond}: {qty:,.0f} units (${value:,.0f})")
        print(f"  Total Investment Required: ${total_invested:,.0f}")

        # Compare costs
        duration_cost = (
            duration_result["portfolio_pv"] if duration_result["success"] else 0
        )
        cashflow_cost = cashflow_result["total_cost"]
        if duration_cost > 0:
            cost_diff = (cashflow_cost - duration_cost) / duration_cost * 100
            print(
                f"\n  Cash flow matching is {cost_diff:.1f}% more expensive than duration matching"
            )
    else:
        print("✗ Cash flow matching optimization failed")

    # Perform analysis on duration matching result
    if duration_result["success"]:
        print("\n3. Risk Analysis")
        print("-" * 40)

        analyzer = HedgingAnalyzer(
            liabilities, bonds, duration_result["quantities"], yield_curve
        )

        # Sensitivity analysis
        shifts = np.linspace(-0.03, 0.03, 13)  # ±300 basis points
        fig, sensitivity = analyzer.sensitivity_analysis(yield_shifts=shifts)

        # Extract key metrics
        tracking_errors = [abs(e) * 100 for e in sensitivity["tracking_errors"]]
        max_error = max(tracking_errors)
        mean_error = np.mean(tracking_errors)

        print("  Interest Rate Sensitivity (±300 bps):")
        print(f"  - Maximum Tracking Error: {max_error:.2f}%")
        print(f"  - Average Tracking Error: {mean_error:.2f}%")
        print(f"  - Risk Reduction: ~{100 - max_error:.0f}%")

        # Value at risk
        liability_changes = [
            (pv / duration_result["liability_pv"] - 1) * 100
            for pv in sensitivity["liability_pvs"]
        ]
        portfolio_changes = [
            (pv / duration_result["portfolio_pv"] - 1) * 100
            for pv in sensitivity["asset_pvs"]
        ]

        print("\n  Extreme Scenarios:")
        print("  - If rates rise 300bps:")
        print(f"    Liability value change: {liability_changes[-1]:.1f}%")
        print(f"    Portfolio value change: {portfolio_changes[-1]:.1f}%")
        print("  - If rates fall 300bps:")
        print(f"    Liability value change: {liability_changes[0]:.1f}%")
        print(f"    Portfolio value change: {portfolio_changes[0]:.1f}%")

        # Create cashflow visualization
        print("\n4. Creating Visualizations...")
        cf_fig = analyzer.create_cashflow_comparison()
        print("   ✓ Cashflow comparison created")
        print("   ✓ Sensitivity analysis created")

        # Save results
        print("\n5. Saving Results...")
        cf_fig.savefig("insurance_cashflows.png", dpi=300, bbox_inches="tight")
        fig.savefig("insurance_sensitivity.png", dpi=300, bbox_inches="tight")
        print("   ✓ Charts saved as PNG files")

    print("\n=== Analysis Complete ===")

    # Display charts
    import matplotlib.pyplot as plt

    plt.show()


if __name__ == "__main__":
    main()
