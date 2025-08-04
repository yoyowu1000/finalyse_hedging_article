"""Optimization algorithms for liability hedging."""

import numpy as np
from scipy.optimize import minimize, linprog
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
            [calculate_bond_present_value(bond, self.yield_curve) for bond in self.bonds]
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
        x0 = np.ones(len(self.bonds))

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            constraints=constraints,
            bounds=bounds,
            options={"disp": False, "maxiter": 1000},
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

    def cash_flow_matching(self) -> dict:
        """Implements exact cash flow matching optimization.

        Returns:
            Dictionary with optimization results
        """
        # Create time grid
        liability_times = sorted(
            set(liability.time_years for liability in self.liabilities)
        )
        bond_cashflow_times = set()
        for bond in self.bonds:
            for t, _ in calculate_bond_cashflows(bond):
                bond_cashflow_times.add(t)

        all_times = sorted(liability_times)  # Only match at liability times

        # Build constraint matrix
        n_times = len(all_times)
        n_bonds = len(self.bonds)

        A = np.zeros((n_times, n_bonds))
        b = np.zeros(n_times)

        # Fill constraint matrix
        for i, t in enumerate(all_times):
            # Liability at time t
            b[i] = sum(liability.amount for liability in self.liabilities)

            # Bond cashflows at time t
            for j, bond in enumerate(self.bonds):
                bond_cf = sum(
                    cf
                    for time, cf in calculate_bond_cashflows(bond)
                    if abs(time - t) < 0.001
                )
                A[i, j] = bond_cf

        # Objective: minimize cost (present value of bonds)
        c = np.array(
            [calculate_bond_present_value(bond, self.yield_curve) for bond in self.bonds]
        )

        # Solve linear program: min c'x subject to Ax >= b, x >= 0
        result = linprog(
            c,
            A_ub=-A,
            b_ub=-b,
            bounds=(0, None),
            method="highs",
            options={"disp": False},
        )

        if not result.success:
            warnings.warn(f"Cash flow matching optimization failed: {result.message}")

        # Calculate metrics
        quantities = result.x if result.success else np.zeros(n_bonds)

        return {
            "quantities": quantities,
            "success": result.success,
            "total_cost": result.fun if result.success else 0,
            "bond_allocations": [
                (bond, qty) for bond, qty in zip(self.bonds, quantities) if qty > 0.01
            ],
        }
