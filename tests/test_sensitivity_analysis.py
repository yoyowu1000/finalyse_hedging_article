"""Test the updated sensitivity analysis with convexity analysis."""

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


def test_sensitivity_analysis_with_convexity(sample_liabilities, sample_bonds, sample_yield_curve):
    """Test that sensitivity analysis includes convexity analysis."""
    # Run optimization
    optimizer = HedgingOptimizer(sample_liabilities, sample_bonds, sample_yield_curve)
    duration_result = optimizer.duration_matching()

    # Create analyzer
    analyzer = HedgingAnalyzer(
        sample_liabilities, sample_bonds, duration_result["quantities"], sample_yield_curve
    )
    
    # Run sensitivity analysis
    fig, results = analyzer.sensitivity_analysis()
    
    # Verify figure was created
    assert fig is not None
    
    # Verify all expected results are present
    assert "yield_shifts" in results
    assert "liability_pvs" in results
    assert "asset_pvs" in results
    assert "hedge_ratios" in results
    assert "tracking_errors" in results
    assert "asset_convexity" in results
    assert "liability_convexity" in results
    assert "convexity_effects" in results
    
    # Verify convexity values are reasonable
    assert results["asset_convexity"] > 0
    assert results["liability_convexity"] > 0
    assert len(results["convexity_effects"]) == len(results["yield_shifts"])
    
    # Verify figure has 4 subplots
    axes = fig.get_axes()
    assert len(axes) == 4
    
    # Verify subplot titles
    expected_titles = [
        "Interest Rate Sensitivity Analysis",
        "Hedge Ratio Stability",
        "Tracking Error Analysis",
        "Convexity Analysis"
    ]
    
    actual_titles = [ax.get_title() for ax in axes]
    for expected in expected_titles:
        assert any(expected == title for title in actual_titles), f"Missing expected title: {expected}"


def test_tracking_error_explanation_present(sample_liabilities, sample_bonds, sample_yield_curve):
    """Test that tracking error explanation is present in the visualization."""
    # Run optimization
    optimizer = HedgingOptimizer(sample_liabilities, sample_bonds, sample_yield_curve)
    duration_result = optimizer.duration_matching()

    # Create analyzer
    analyzer = HedgingAnalyzer(
        sample_liabilities, sample_bonds, duration_result["quantities"], sample_yield_curve
    )
    
    # Run sensitivity analysis
    fig, _ = analyzer.sensitivity_analysis()
    
    # Find the tracking error analysis subplot
    axes = fig.get_axes()
    tracking_error_ax = None
    for ax in axes:
        if ax.get_title() == "Tracking Error Analysis":
            tracking_error_ax = ax
            break
    
    assert tracking_error_ax is not None
    
    # Check that explanatory text is present
    texts = tracking_error_ax.texts
    assert len(texts) > 0
    
    # Verify the explanation contains key phrases
    explanation_found = False
    for text in texts:
        if "Tracking Error" in text.get_text() and "perfect hedge" in text.get_text():
            explanation_found = True
            break
    
    assert explanation_found, "Tracking error explanation not found in subplot"