---
created: 2025-08-05
edited: 2025-08-05
modified:
  - 2025-06-19
  - 2025-06-29
  - 2025-06-30
  - 2025-08-04
  - 2025-08-05
linter-yaml-title-alias: "Hedging Liability Cashflows with Python: A Concise Guide"
aliases:
  - "Hedging Liability Cashflows with Python: A Concise Guide"
  - Python Hedging Tutorial v3
tags:
  - para/pro/finalyse/proj/2025/interest-rate-article
---

# Hedging Liability Cashflows with Python: A Concise Guide

## Why Hedging is Necessary

typically, we take a risk where we want to achieve profits. and for insurance companies or for certain lines of business, we want to hedge out the risks that we believe won't create appropriate risk-adjusted returns. a clear example of this is interest rate risk for certain life insurance companies, where we sell annuities but don't want to take on the risk or market risk from investing in annuity funding.

## Why hedge programmatically

hedging programmatically helps us create a model that will help us understand how assets and liabilities relate to each other. with Python, it is relatively easier compared to other programming languages, and can help us sense-check results from other more sophisticated hedging applications, or simply create a script that we can run periodically to determine the appropriate hedging portfolio for say a small book of liabilities

## Python Prerequisites & Limitations

### Requirements

**What You Need:**

- Python 3.10+ environment
- Historical yield curve data
- Bond universe details (maturities, coupons)

**What This Example Doesn't Handle:**

- Credit risk (default probability)
- Callable or convertible bonds
- Multi-currency portfolios
- Liquidity constraints
- Non-parallel yield curve shifts (requires convexity adjustments)

### Resources

- code can be found here: https://github.com/yoyowu1000/finalyse_hedging_article

## Core Concepts That Are Relevant

### Understanding the Building Blocks

in our example, we'll focus more on duration, as specifically macauly duration, to match our liabilities and assets. 

although not precise, duration can be seen as the sensitivity of your portfolio relative to interest rate changes. for example, a 5-year duration means that a 1% increase causes approximately 5% portfolio value loss

we also examine convexity, and convexity helps us understand the nonlinear relationship of our portfolio's price change relative to interest rate changes. in other words, it helps correct our assumption that prices change linearly when they don't

## Getting Started with the Code

To begin hedging with Python, we'll use the example code from `examples/insurance_company.py`. Here's how we structure the key components:

**Creating Liabilities:**

```python
liabilities = [
    Liability(time_years=1, amount=1_000),  # €1M in 1 year
    Liability(time_years=5, amount=2_500),  # €2.5M in 5 years
    Liability(time_years=10, amount=3_200), # €3.2M in 10 years
]
```

**Defining Available Bonds:**

```python
bonds = [
    Bond(maturity_years=2, coupon_rate=0.025, face_value=1),
    Bond(maturity_years=5, coupon_rate=0.032, face_value=1),
    Bond(maturity_years=10, coupon_rate=0.038, face_value=1),
]
```

**Running the Optimization:**

```python
optimizer = HedgingOptimizer(liabilities, bonds, yield_curve)
result = optimizer.duration_matching()
```

The code handles all the calculations and returns optimal bond quantities that minimize interest rate risk.

### Explaining the Models

The hedging framework uses three core Pydantic models that ensure data integrity through validation:

**1. Liability Model:**

```python
Liability(time_years=5, amount=1_000_000)
```

- Represents future payment obligations
- Validates that time is positive and amount is non-negative
- Immutable design prevents accidental modifications

**2. Bond Model:**

```python
Bond(maturity_years=10, coupon_rate=0.03, face_value=1_000_000)
```

- Models fixed-income securities with annual coupons
- Generates cashflow schedule automatically
- Calculates present value and duration using yield curve data

**3. YieldCurve Model:**

```python
YieldCurve(times=[1, 2, 5, 10], rates=[0.02, 0.025, 0.03, 0.035])
```

- Stores term structure of interest rates
- Provides linear interpolation for any maturity
- Used for discounting all future cashflows

These models work together: the YieldCurve provides discount rates, Bonds generate cashflows based on their terms, and Liabilities represent the obligations we need to hedge.

### Explaining how optimisations works

The duration matching optimization minimizes interest rate risk by aligning the weighted average duration of assets and liabilities:

**The Optimization Process:**

1. **Calculate Liability Duration:**
   - Each liability's duration equals its time to payment
   - Portfolio duration = weighted average by present value
   
2. **Set Up the Objective:**

```python
   minimize: Σ(bond_quantities²)
```

   - Minimizes concentration risk by penalizing large positions
   - Duration matching is enforced through constraints, not the objective
   - Results in a diversified portfolio spread across multiple bonds

1. **Apply Constraints:**
   - **Duration equality**: Portfolio duration = Liability duration (enforced as equality constraint)
   - **Full funding**: Total asset value ≥ Total liability value (inequality constraint)
   - **No short selling**: Bond quantities ≥ 0 (bounds constraint)
   - Optional: Maximum position sizes

2. **Solve Using SciPy:**

```python
   result = scipy.optimize.minimize(
       objective_function,
       initial_guess,
       method='SLSQP',
       constraints=constraints
   )
```

**Why Duration Matching Works:**
- When durations match, portfolio value changes from interest rate movements are approximately equal for assets and liabilities
- A 1% rate increase affects both sides similarly, maintaining the funding ratio
- Achieves 85-90% hedge effectiveness for parallel yield curve shifts

The optimizer returns optimal bond quantities that create a self-financing portfolio with minimal interest rate sensitivity.

## Conclusion

Interest rate hedging isn't optional in today's volatile environment. With the code snippets above that can be found in the repo, you now have a starting point to implement hedging that reduces risk while potentially saving significant regulatory capital. The code can be further enhanced to your organisational or personal requirements.

## Next Steps and Contact

please feel free to contact me at yuan-yow.wu@finalyse.com 
