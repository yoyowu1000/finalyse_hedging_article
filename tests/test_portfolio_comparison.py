"""Test the updated portfolio comparison visualization."""

import numpy as np
import pytest
from src.models import Liability, Bond, YieldCurve
from src.optimizer import HedgingOptimizer
from src.analyzer import HedgingAnalyzer


@pytest.fixture
def sample_liabilities():
    """Create sample liabilities for testing."""
    return [
        Liability(time_years=1, amount=1_000_000),
        Liability(time_years=5, amount=2_000_000),
        Liability(time_years=10, amount=3_000_000),
    ]


@pytest.fixture
def sample_bonds():
    """Create sample bonds for testing."""
    return [
        Bond(maturity_years=2, coupon_rate=0.03, face_value=1000),
        Bond(maturity_years=5, coupon_rate=0.035, face_value=1000),
        Bond(maturity_years=10, coupon_rate=0.04, face_value=1000),
    ]


@pytest.fixture
def sample_yield_curve():
    """Create sample yield curve for testing."""
    return YieldCurve(
        times=[1, 2, 5, 10, 20],
        rates=[0.02, 0.025, 0.03, 0.035, 0.04],
    )


def test_portfolio_comparison_visualization(sample_liabilities, sample_bonds, sample_yield_curve):
    """Test that portfolio comparison visualization is created successfully."""
    # Run optimization
    optimizer = HedgingOptimizer(sample_liabilities, sample_bonds, sample_yield_curve)
    
    # Get duration-matched portfolio
    duration_result = optimizer.duration_matching()
    
    # Create initial portfolio (equal weights as example)
    initial_quantities = np.array([1000, 1000, 1000])

    # Create analyzer
    analyzer = HedgingAnalyzer(
        sample_liabilities, sample_bonds, duration_result["quantities"], sample_yield_curve
    )
    
    # Create comparison visualization
    fig = analyzer.create_portfolio_comparison(
        initial_quantities=initial_quantities,
        optimized_quantities=duration_result["quantities"],
        optimization_type="Duration Matching",
    )
    
    # Verify figure was created
    assert fig is not None
    
    # Verify figure has expected subplots (3x2 grid)
    axes = fig.get_axes()
    assert len(axes) == 4  # 3 rows x 2 columns, but last row spans both columns
    
    # Verify titles
    expected_titles = [
        "Bond Allocation Comparison",
        "Cash Flow Profiles Comparison", 
        "Portfolio Metrics Comparison",
        "Tracking Error Comparison"
    ]
    
    actual_titles = [ax.get_title() for ax in axes]
    for expected in expected_titles:
        assert any(expected in title for title in actual_titles), f"Missing expected title: {expected}"