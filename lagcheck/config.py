"""Keep private runtime data outside the source tree and the portable bundle."""

import os
from pathlib import Path

DATA = Path(
    os.environ.get("LAGCHECK_DATA_DIR")
    or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LagCheck"
)
RESOURCES = Path(__file__).resolve().parent / "resources"
