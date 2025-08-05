# Python Liability Hedging

An example Python implementation showing how to hedge liability cash flows with bonds. This library demonstrates duration matching techniques for managing interest rate risk.

## Features

- **Duration Matching**
- **Visualization**
- **Validation with Pydantic**

## Quick Start

### Prerequisites

This project uses [UV](https://docs.astral.sh/uv/) as the package manager. UV is an extremely fast Python package and project manager, written in Rust.

#### Installing UV

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Using Homebrew
brew install uv
```

For more installation options, visit the [official UV documentation](https://docs.astral.sh/uv/).

### Installation

After installing UV, simply run:

```bash
# TODO: TBU
git clone <repository-url> 
cd hedging_article
uv sync
```

That's it! `uv sync` will:

- Create a virtual environment automatically
- Install all dependencies with exact versions from the `uv.lock` file
- Ensure your environment matches the project's requirements exactly

### Basic Example

```python
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
yield_curve = YieldCurve(
    times=[1, 2, 5, 10],
    rates=[0.02, 0.025, 0.03, 0.035]
)

# Optimize
optimizer = HedgingOptimizer(liabilities, bonds, yield_curve)
result = optimizer.duration_matching()
```

## Examples

- `examples/quick_start.py` - Minimal working example
- `examples/insurance_company.py` - Real-world insurance case study

## Testing

```bash
python -m pytest tests/
```

## License

MIT License - See LICENSE file for details

## Citation

If you use this code in your research, please cite:

```
@article{yoyowu2025hedging,
  title={Hedging Liability Cashflows with Python},
  author={yoyowu1000},
  year={2025},
  url={https://github.com/yoyowu1000/python-liability-hedging}
}
```
