# Troubleshooting Guide

## Common Issues and Solutions

### 1. Optimization Fails

**Symptom**: `optimizer.duration_matching()` returns `success: False`

**Possible Causes & Solutions**:

- **No feasible solution exists**
  - Add more bonds with different maturities
  - Check if liability duration is outside the range of available bonds
  - Consider adjusting the optimization constraints

- **Numerical issues**
  - Scale your amounts (use thousands or millions instead of units)
  - Check for very small or very large numbers

- **Constraint conflicts**
  - Ensure liability PV is positive
  - Verify yield curve rates are reasonable

### 2. Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'src'`

**Solution**: 
```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
```

### 3. Validation Errors

**Symptom**: `ValidationError` when creating models

**Common Issues**:
- Negative time values (must be positive)
- Zero or negative amounts (must be positive)
- Mismatched array lengths in YieldCurve
- Non-ascending time points in YieldCurve

### 4. Memory Issues

**Symptom**: Large portfolios cause memory errors

**Solutions**:
- Process in batches
- Use sparse matrices for very large problems
- Optimize the number of bonds in the portfolio

### 5. Visualization Issues

**Symptom**: Charts don't display or save incorrectly

**Solutions**:
```python
# For display issues
import matplotlib
matplotlib.use('TkAgg')  # or 'Qt5Agg'

# For saving issues
fig.savefig('output.png', dpi=300, bbox_inches='tight')
```

### 6. Performance Issues

**Symptom**: Optimization takes too long

**Solutions**:
- Reduce the number of bonds in the universe
- Consider simplifying the optimization problem
- Set looser convergence criteria:
  ```python
  result = minimize(..., options={'ftol': 1e-6})
  ```

## Debug Mode

Enable detailed output for debugging:

```python
# In optimizer
result = minimize(..., options={'disp': True})

# Print intermediate values
print(f"Liability PV: {liability_pv}")
print(f"Bond PVs: {bond_pvs}")
print(f"Initial guess: {x0}")
```

## Getting Help

If you encounter issues not covered here:

1. Check the error message carefully
2. Verify your input data is valid
3. Try the examples first to ensure installation is correct
4. Open an issue on GitHub with:
   - Error message
   - Minimal code to reproduce
   - Your environment (Python version, OS)