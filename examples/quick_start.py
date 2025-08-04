"""Quick start example for liability hedging."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.models import Liability, Bond, YieldCurve
from src.optimizer import HedgingOptimizer
from src.analyzer import HedgingAnalyzer


def main():
    """Run a simple hedging example."""

    print("=== Liability Hedging Quick Start ===\n")

    # Step 1: Define your liabilities
    print("1. Defining liabilities...")
    liabilities = [
        Liability(time_years=1, amount=1_000_000),
        Liability(time_years=5, amount=2_000_000),
        Liability(time_years=10, amount=3_000_000),
    ]

    for liability in liabilities:
        print(f"   {liability}")

    # Step 2: Define available bonds
    print("\n2. Available bonds for hedging...")
    bonds = [
        Bond(maturity_years=2, coupon_rate=0.03, face_value=1000),
        Bond(maturity_years=5, coupon_rate=0.035, face_value=1000),
        Bond(maturity_years=10, coupon_rate=0.04, face_value=1000),
    ]

    for bond in bonds:
        print(f"   {bond}")

    # Step 3: Define current yield curve
    print("\n3. Current yield curve...")
    yield_curve = YieldCurve(
        times=[1, 2, 5, 10, 20], rates=[0.02, 0.025, 0.03, 0.035, 0.04]
    )

    for t, r in zip(yield_curve.times, yield_curve.rates):
        print(f"   {t}Y: {r:.1%}")

    # Step 4: Run optimization
    print("\n4. Running duration matching optimization...")
    optimizer = HedgingOptimizer(liabilities, bonds, yield_curve)
    result = optimizer.duration_matching()

    # Step 5: Display results
    print("\n5. Optimization Results:")
    print(f"   Success: {result['success']}")
    print(f"   Liability PV: ${result['liability_pv']:,.0f}")
    print(f"   Liability Duration: {result['liability_duration']:.2f} years")
    print(f"   Portfolio PV: ${result['portfolio_pv']:,.0f}")
    print(f"   Portfolio Duration: {result['portfolio_duration']:.2f} years")

    print("\n   Optimal Bond Portfolio:")
    for bond, quantity in result["bond_allocations"]:
        print(f"   - {bond}: {quantity:,.0f} units")

    # Step 6: Create visualization
    print("\n6. Creating visualization...")
    analyzer = HedgingAnalyzer(liabilities, bonds, result["quantities"], yield_curve)

    # Create cashflow comparison
    analyzer.create_cashflow_comparison()
    print("   ✓ Cashflow comparison chart created")

    # Create sensitivity analysis
    fig2, sensitivity_results = analyzer.sensitivity_analysis()
    print("   ✓ Sensitivity analysis completed")

    # Show risk reduction
    tracking_errors = sensitivity_results["tracking_errors"]
    max_error = max(abs(e) for e in tracking_errors) * 100
    print(f"\n   Maximum tracking error: {max_error:.2f}%")
    print(f"   Risk reduction achieved: ~{100 - max_error:.0f}%")

    print("\n=== Quick Start Complete ===")
    print("Charts will be displayed. Close them to exit.")

    # Display charts
    import matplotlib.pyplot as plt

    plt.show()


if __name__ == "__main__":
    main()
