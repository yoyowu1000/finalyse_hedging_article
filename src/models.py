"""Data models for liability hedging with Pydantic validation."""

from pydantic import BaseModel, Field, field_validator
import numpy as np
from typing import Optional


class Liability(BaseModel):
    """Represents a single liability cashflow.
    
    Attributes:
        time_years: Time to payment in years (must be positive)
        amount: Payment amount (must be positive)
    """
    time_years: float = Field(..., gt=0, description="Time to payment in years")
    amount: float = Field(..., gt=0, description="Payment amount")
    
    class Config:
        frozen = True  # Make immutable
        
    def __repr__(self):
        return f"Liability(t={self.time_years}Y, amount=${self.amount:,.0f})"


class Bond(BaseModel):
    """Represents a fixed-rate bond.
    
    Attributes:
        maturity_years: Bond maturity in years (must be positive)
        coupon_rate: Annual coupon rate (must be non-negative)
        face_value: Face value of the bond (must be positive)
        price: Market price if different from par (optional)
    """
    maturity_years: float = Field(..., gt=0, description="Bond maturity in years")
    coupon_rate: float = Field(..., ge=0, description="Annual coupon rate")
    face_value: float = Field(..., gt=0, description="Face value of the bond")
    price: Optional[float] = Field(None, gt=0, description="Market price if different from par")
    
    class Config:
        frozen = True
        
    def __repr__(self):
        return f"Bond({self.maturity_years}Y, {self.coupon_rate:.1%}, FV=${self.face_value:,.0f})"


class YieldCurve(BaseModel):
    """Represents a yield curve with interpolation capabilities.
    
    Attributes:
        times: Time points for yield curve
        rates: Interest rates at time points
    """
    times: list[float] = Field(..., description="Time points for yield curve")
    rates: list[float] = Field(..., description="Interest rates at time points")
    
    @field_validator('rates')
    def validate_rates_length(cls, v, info):
        times = info.data.get('times', [])
        if len(v) != len(times):
            raise ValueError("Times and rates must have same length")
        return v
    
    @field_validator('times')
    def validate_times_ascending(cls, v):
        if not all(t1 < t2 for t1, t2 in zip(v[:-1], v[1:])):
            raise ValueError("Times must be in ascending order")
        return v
    
    def model_post_init(self, __context):
        """Initialize numpy arrays after validation."""
        self._times_array = np.array(self.times)
        self._rates_array = np.array(self.rates)
    
    class Config:
        arbitrary_types_allowed = True
    
    def get_rate(self, time: float) -> float:
        """Get interpolated rate for given time."""
        return float(np.interp(time, self._times_array, self._rates_array))
    
    def get_discount_factor(self, time: float) -> float:
        """Get discount factor for given time using continuous compounding."""
        rate = self.get_rate(time)
        return np.exp(-rate * time)
    
    def shift_parallel(self, shift: float) -> 'YieldCurve':
        """Create new curve with parallel shift."""
        return YieldCurve(
            times=self.times,
            rates=[r + shift for r in self.rates]
        )