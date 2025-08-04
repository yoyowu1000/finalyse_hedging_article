"""Template for customizing liability hedging for your specific needs."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.models import Liability, Bond, YieldCurve
from src.optimizer import HedgingOptimizer
from src.analyzer import HedgingAnalyzer


# ============================================================================
# STEP 1: Define Your Liabilities
# ============================================================================
# Replace these with your actual liability schedule
# Each liability needs:
# - time_years: When the payment is due (in years from now)
# - amount: How much needs to be paid

YOUR_LIABILITIES = [
    Liability(time_years=1, amount=1_000_000),    # Example: $1M due in 1 year
    Liability(time_years=3, amount=2_500_000),    # Example: $2.5M due in 3 years
    Liability(time_years=5, amount=1_500_000),    # Example: $1.5M due in 5 years
    # Add more liabilities as needed...
]


# ============================================================================
# STEP 2: Define Available Bonds
# ============================================================================
# Replace with bonds available in your market
# Each bond needs:
# - maturity_years: When the bond matures
# - coupon_rate: Annual coupon rate (e.g., 0.03 for 3%)
# - face_value: Face value of one bond unit

YOUR_BONDS = [
    Bond(maturity_years=2, coupon_rate=0.025, face_value=1000),
    Bond(maturity_years=5, coupon_rate=0.030, face_value=1000),
    Bond(maturity_years=10, coupon_rate=0.035, face_value=1000),
    # Add more bonds as needed...
]


# ============================================================================
# STEP 3: Define Current Yield Curve
# ============================================================================
# Replace with current market rates
# - times: Maturity points (in years)
# - rates: Interest rates at those maturities

YOUR_YIELD_CURVE = YieldCurve(
    times=[1, 2, 5, 10, 20],
    rates=[0.02, 0.025, 0.03, 0.035, 0.04]  # 2%, 2.5%, 3%, 3.5%, 4%
)


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================
def run_hedging_analysis():
    """Run your customized hedging analysis."""
    
    print("=== Custom Liability Hedging Analysis ===\n")
    
    # Use your data
    liabilities = YOUR_LIABILITIES
    bonds = YOUR_BONDS
    yield_curve = YOUR_YIELD_CURVE
    
    # Run optimization
    print("Running optimization...")
    optimizer = HedgingOptimizer(liabilities, bonds, yield_curve)
    
    # Try duration matching first
    result = optimizer.duration_matching()
    
    if not result['success']:
        print("Duration matching failed, trying cash flow matching...")
        result = optimizer.cash_flow_matching()
    
    # Display results
    if result['success']:
        print("\n✓ Optimization Successful!")
        print("\nOptimal Portfolio:")
        
        total_cost = 0
        for bond, qty in result.get('bond_allocations', []):
            cost = qty * bond.face_value
            total_cost += cost
            print(f"  Buy {qty:,.0f} units of {bond}")
            print(f"    Cost: ${cost:,.0f}")
        
        print(f"\nTotal Investment Required: ${total_cost:,.0f}")
        
        # Create visualizations
        print("\nCreating analysis charts...")
        analyzer = HedgingAnalyzer(liabilities, bonds, result['quantities'], yield_curve)
        
        # Cashflow comparison
        cf_fig = analyzer.create_cashflow_comparison('my_cashflows.png')
        print("  ✓ Saved cashflow comparison to 'my_cashflows.png'")
        
        # Sensitivity analysis
        sens_fig, sens_data = analyzer.sensitivity_analysis('my_sensitivity.png')
        print("  ✓ Saved sensitivity analysis to 'my_sensitivity.png'")
        
        # Risk metrics
        max_error = max(abs(e) for e in sens_data['tracking_errors']) * 100
        print(f"\nRisk Analysis:")
        print(f"  Maximum tracking error: {max_error:.2f}%")
        print(f"  Hedge effectiveness: ~{100 - max_error:.0f}%")
        
    else:
        print("\n✗ Optimization failed!")
        print("Possible reasons:")
        print("  - No feasible solution exists with available bonds")
        print("  - Constraints are too restrictive")
        print("  - Try adding more bonds with different maturities")
    
    print("\n=== Analysis Complete ===")
    
    # Show charts
    import matplotlib.pyplot as plt
    plt.show()


# ============================================================================
# ADVANCED CUSTOMIZATION OPTIONS
# ============================================================================

# Option 1: Add constraints (e.g., maximum position size)
def add_position_limits(optimizer, max_position=10000):
    """Example of adding custom constraints."""
    # This would require modifying the optimizer class
    pass

# Option 2: Include transaction costs
def calculate_transaction_costs(quantities, cost_per_bond=10):
    """Calculate total transaction costs."""
    return sum(q * cost_per_bond for q in quantities if q > 0)

# Option 3: Multi-currency hedging
def convert_to_base_currency(amount, fx_rate):
    """Convert foreign currency liabilities."""
    return amount * fx_rate


if __name__ == "__main__":
    run_hedging_analysis()