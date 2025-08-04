from src.models import Liability, Bond, YieldCurve
from src.optimizer import HedgingOptimizer

# Define liabilities (e.g., insurance claims)
liabilities = [
    Liability(time_years=1, amount=1_000_000),
    Liability(time_years=5, amount=2_000_000),
]

# Available bonds
bonds = [
    Bond(maturity_years=2, coupon_rate=0.03, face_value=1000),
    Bond(maturity_years=5, coupon_rate=0.035, face_value=1000),
]

# Current yield curve
yield_curve = YieldCurve(times=[1, 2, 5, 10], rates=[0.02, 0.025, 0.03, 0.035])

# Optimize
optimizer = HedgingOptimizer(liabilities, bonds, yield_curve)
result = optimizer.duration_matching()
print(result)
