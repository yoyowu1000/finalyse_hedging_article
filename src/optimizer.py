"""Optimization algorithms for liability hedging."""

import numpy as np
from scipy.optimize import minimize
import warnings
from .models import Liability, Bond, YieldCurve


def calculate_bond_cashflows(bond: Bond) -> list[tuple[float, float]]:
    """Calculate all cashflows for a bond.

    Args:
        bond: Bond object

    Returns:
        List of (time, cashflow) tuples
    """
    cashflows = []

    # Annual coupon payments
    coupon_payment = bond.face_value * bond.coupon_rate

    # Handle bonds with maturity less than 1 year
    if bond.maturity_years < 1:
        # Single payment at maturity with prorated coupon
        final_coupon = bond.face_value * bond.coupon_rate * bond.maturity_years
        cashflows.append((bond.maturity_years, final_coupon + bond.face_value))
    else:
        # Add coupon payments
        for year in range(1, int(bond.maturity_years) + 1):
            if year < bond.maturity_years:
                cashflows.append((float(year), coupon_payment))
            else:
                # Final payment includes both coupon and principal
                cashflows.append((float(year), coupon_payment + bond.face_value))

        # Handle fractional final period if maturity is not whole number
        if bond.maturity_years != int(bond.maturity_years):
            # Remove the last added cashflow and recalculate
            cashflows.pop()
            fractional_period = bond.maturity_years - int(bond.maturity_years)
            final_coupon = bond.face_value * bond.coupon_rate * fractional_period
            cashflows.append((bond.maturity_years, final_coupon + bond.face_value))

    return cashflows


def calculate_present_value(
    cashflows: list[tuple[float, float]], yield_curve: YieldCurve
) -> float:
    """Calculate present value of cashflows using yield curve."""
    pv = 0.0
    for time, amount in cashflows:
        discount_factor = yield_curve.get_discount_factor(time)
        pv += amount * discount_factor
    return pv


def calculate_bond_present_value(bond: Bond, yield_curve: YieldCurve) -> float:
    """Calculate present value of a bond using its cashflows and the yield curve.

    Args:
        bond: Bond object
        yield_curve: YieldCurve object for discounting

    Returns:
        Present value of the bond
    """
    cashflows = calculate_bond_cashflows(bond)
    return calculate_present_value(cashflows, yield_curve)


def calculate_duration(bond: Bond, yield_curve: YieldCurve) -> float:
    """Calculate modified duration of a bond."""
    cashflows = calculate_bond_cashflows(bond)
    pv = calculate_bond_present_value(bond, yield_curve)

    if pv == 0:
        return 0.0

    weighted_time = 0.0
    for time, amount in cashflows:
        discount_factor = yield_curve.get_discount_factor(time)
        weighted_time += time * amount * discount_factor

    macaulay_duration = weighted_time / pv

    # Convert to modified duration
    avg_yield = yield_curve.get_rate(bond.maturity_years / 2)
    modified_duration = macaulay_duration / (1 + avg_yield)

    return modified_duration


class HedgingOptimizer:
    """Handles various hedging optimization strategies."""

    def __init__(
        self, liabilities: list[Liability], bonds: list[Bond], yield_curve: YieldCurve
    ):
        """Initialize optimizer with market data.

        Args:
            liabilities: List of liability cashflows
            bonds: List of available bonds
            yield_curve: Current yield curve
        """
        self.liabilities = liabilities
        self.bonds = bonds
        self.yield_curve = yield_curve

    def duration_matching(self) -> dict:
        """Implements duration matching with PV constraint.

        Returns:
            Dictionary with optimization results
        """
        # Calculate liability portfolio metrics
        liability_pv = sum(
            liability.amount
            * self.yield_curve.get_discount_factor(liability.time_years)
            for liability in self.liabilities
        )

        if liability_pv == 0:
            raise ValueError("Liability present value is zero")

        liability_duration = (
            sum(
                liability.amount
                * liability.time_years
                * self.yield_curve.get_discount_factor(liability.time_years)
                for liability in self.liabilities
            )
            / liability_pv
        )

        # Bond metrics
        bond_pvs = np.array(
            [
                calculate_bond_present_value(bond, self.yield_curve)
                for bond in self.bonds
            ]
        )
        bond_durations = np.array(
            [calculate_duration(bond, self.yield_curve) for bond in self.bonds]
        )

        def objective(x):
            """Minimize tracking error (sum of squares for diversification)."""
            return np.sum(x**2)

        def pv_constraint(x):
            """Present value must match liabilities."""
            return np.dot(x, bond_pvs) - liability_pv

        def duration_constraint(x):
            """Duration must match liabilities."""
            portfolio_pv = np.dot(x, bond_pvs)
            if portfolio_pv == 0:
                return 0
            portfolio_duration = np.dot(x * bond_pvs, bond_durations) / portfolio_pv
            return portfolio_duration - liability_duration

        constraints = [
            {"type": "eq", "fun": pv_constraint},
            {"type": "eq", "fun": duration_constraint},
        ]

        bounds = [(0, None) for _ in self.bonds]
        # Better initial guess based on liability proportion
        x0 = np.ones(len(self.bonds)) * (liability_pv / sum(bond_pvs))

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            constraints=constraints,
            bounds=bounds,
            options={"disp": False, "maxiter": 100, "ftol": 1e-6},
        )

        if not result.success:
            warnings.warn(f"Duration matching optimization failed: {result.message}")

        return {
            "quantities": result.x,
            "success": result.success,
            "liability_pv": liability_pv,
            "liability_duration": liability_duration,
            "portfolio_pv": np.dot(result.x, bond_pvs) if result.success else 0,
            "portfolio_duration": (
                np.dot(result.x * bond_pvs, bond_durations) / np.dot(result.x, bond_pvs)
            )
            if result.success and np.dot(result.x, bond_pvs) > 0
            else 0,
            "bond_allocations": [
                (bond, qty) for bond, qty in zip(self.bonds, result.x) if qty > 0.01
            ],
        }


    def create_initial_portfolio(self) -> dict:
        """Create an initial unoptimized portfolio using maturity bucketing.
        
        This represents a naive approach where bonds are allocated based on
        maturity buckets to roughly match liability timings.
        
        Returns:
            Dictionary with portfolio details
        """
        # Calculate total liability PV
        liability_pv = sum(
            liability.amount * self.yield_curve.get_discount_factor(liability.time_years)
            for liability in self.liabilities
        )
        
        # Create maturity buckets for liabilities
        liability_buckets = {}
        bucket_size = 2.0  # 2-year buckets
        
        for liability in self.liabilities:
            bucket = int(liability.time_years / bucket_size) * bucket_size
            if bucket not in liability_buckets:
                liability_buckets[bucket] = []
            liability_buckets[bucket].append(liability)
        
        # Calculate PV for each bucket
        bucket_pvs = {}
        for bucket, liabs in liability_buckets.items():
            bucket_pv = sum(
                liability.amount * self.yield_curve.get_discount_factor(liability.time_years)
                for liability in liabs
            )
            bucket_pvs[bucket] = bucket_pv
        
        # Allocate bonds to buckets based on maturity
        bond_allocations = np.zeros(len(self.bonds))
        
        for bucket, target_pv in bucket_pvs.items():
            # Find bonds with maturities close to this bucket
            bucket_bonds = []
            for i, bond in enumerate(self.bonds):
                bond_bucket = int(bond.maturity_years / bucket_size) * bucket_size
                if abs(bond_bucket - bucket) <= bucket_size:
                    bucket_bonds.append((i, bond))
            
            if not bucket_bonds:
                # If no bonds in this bucket, use all bonds
                bucket_bonds = [(i, bond) for i, bond in enumerate(self.bonds)]
            
            # Allocate proportionally among bonds in this bucket
            if bucket_bonds:
                # Calculate total PV of bonds in bucket (per unit)
                bucket_bond_pvs = [
                    calculate_bond_present_value(bond, self.yield_curve)
                    for _, bond in bucket_bonds
                ]
                total_bucket_bond_pv = sum(bucket_bond_pvs)
                
                # Allocate to match target PV
                for (idx, bond), bond_pv in zip(bucket_bonds, bucket_bond_pvs):
                    if total_bucket_bond_pv > 0:
                        allocation = (target_pv * bond_pv / total_bucket_bond_pv) / bond_pv
                        bond_allocations[idx] += allocation
        
        # Scale allocations to match total liability PV exactly
        current_pv = sum(
            qty * calculate_bond_present_value(bond, self.yield_curve)
            for bond, qty in zip(self.bonds, bond_allocations)
        )
        
        if current_pv > 0:
            scaling_factor = liability_pv / current_pv
            bond_allocations *= scaling_factor
        
        # Calculate portfolio metrics
        portfolio_pv = sum(
            qty * calculate_bond_present_value(bond, self.yield_curve)
            for bond, qty in zip(self.bonds, bond_allocations)
        )
        
        # Calculate portfolio duration
        portfolio_duration = 0
        if portfolio_pv > 0:
            for bond, qty in zip(self.bonds, bond_allocations):
                if qty > 0:
                    bond_pv = calculate_bond_present_value(bond, self.yield_curve)
                    bond_duration = calculate_duration(bond, self.yield_curve)
                    portfolio_duration += (qty * bond_pv * bond_duration) / portfolio_pv
        
        # Calculate liability duration for comparison
        liability_duration = (
            sum(
                liability.amount
                * liability.time_years
                * self.yield_curve.get_discount_factor(liability.time_years)
                for liability in self.liabilities
            )
            / liability_pv
        )
        
        return {
            "quantities": bond_allocations,
            "success": True,
            "liability_pv": liability_pv,
            "liability_duration": liability_duration,
            "portfolio_pv": portfolio_pv,
            "portfolio_duration": portfolio_duration,
            "bond_allocations": [
                (bond, qty) for bond, qty in zip(self.bonds, bond_allocations) if qty > 0.01
            ],
            "strategy": "maturity_bucketing",
        }
