"""Tests for data models."""

import pytest
from pydantic import ValidationError
from src.models import Liability, Bond, YieldCurve


class TestLiability:
    """Test Liability model."""

    def test_valid_liability(self):
        """Test creating valid liability."""
        liability = Liability(time_years=5.0, amount=1000000.0)
        assert liability.time_years == 5.0
        assert liability.amount == 1000000.0

    def test_negative_time_fails(self):
        """Test that negative time raises error."""
        with pytest.raises(ValidationError):
            Liability(time_years=-1.0, amount=1000000.0)

    def test_zero_amount_fails(self):
        """Test that zero amount raises error."""
        with pytest.raises(ValidationError):
            Liability(time_years=5.0, amount=0.0)

    def test_immutability(self):
        """Test that liability is immutable."""
        liability = Liability(time_years=5.0, amount=1000000.0)
        with pytest.raises(ValidationError):
            liability.time_years = 10.0


class TestBond:
    """Test Bond model."""

    def test_valid_bond(self):
        """Test creating valid bond."""
        bond = Bond(maturity_years=10.0, coupon_rate=0.05, face_value=1000.0)
        assert bond.maturity_years == 10.0
        assert bond.coupon_rate == 0.05
        assert bond.face_value == 1000.0
        assert bond.price is None

    def test_bond_with_price(self):
        """Test bond with custom price."""
        bond = Bond(
            maturity_years=10.0, coupon_rate=0.05, face_value=1000.0, price=980.0
        )
        assert bond.price == 980.0

    def test_negative_coupon_fails(self):
        """Test that negative coupon rate raises error."""
        with pytest.raises(ValidationError):
            Bond(maturity_years=10.0, coupon_rate=-0.01, face_value=1000.0)

    def test_zero_coupon_allowed(self):
        """Test that zero coupon is allowed."""
        bond = Bond(maturity_years=10.0, coupon_rate=0.0, face_value=1000.0)
        assert bond.coupon_rate == 0.0


class TestYieldCurve:
    """Test YieldCurve model."""

    def test_valid_yield_curve(self):
        """Test creating valid yield curve."""
        curve = YieldCurve(times=[1, 2, 5], rates=[0.02, 0.025, 0.03])
        assert len(curve.times) == 3
        assert len(curve.rates) == 3

    def test_mismatched_lengths_fail(self):
        """Test that mismatched lengths raise error."""
        with pytest.raises(ValidationError):
            YieldCurve(times=[1, 2, 5], rates=[0.02, 0.025])

    def test_non_ascending_times_fail(self):
        """Test that non-ascending times raise error."""
        with pytest.raises(ValidationError):
            YieldCurve(times=[1, 5, 2], rates=[0.02, 0.03, 0.025])

    def test_interpolation(self):
        """Test rate interpolation."""
        curve = YieldCurve(times=[1, 2, 5], rates=[0.02, 0.025, 0.03])
        # Test exact points
        assert curve.get_rate(1) == 0.02
        assert curve.get_rate(2) == 0.025
        assert curve.get_rate(5) == 0.03
        # Test interpolation
        assert 0.02 < curve.get_rate(1.5) < 0.025
        assert 0.025 < curve.get_rate(3) < 0.03

    def test_discount_factor(self):
        """Test discount factor calculation."""
        curve = YieldCurve(times=[1, 2, 5], rates=[0.02, 0.025, 0.03])
        # Discount factor should be less than 1
        assert curve.get_discount_factor(1) < 1.0
        assert curve.get_discount_factor(5) < 1.0
        # Longer maturity should have lower discount factor
        assert curve.get_discount_factor(5) < curve.get_discount_factor(1)

    def test_parallel_shift(self):
        """Test parallel shift of yield curve."""
        curve = YieldCurve(times=[1, 2, 5], rates=[0.02, 0.025, 0.03])
        shifted = curve.shift_parallel(0.01)
        assert shifted.get_rate(1) == 0.03
        assert shifted.get_rate(2) == 0.035
        assert shifted.get_rate(5) == 0.04
