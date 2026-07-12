"""ML-readiness validation for MyAlert research + outcome datasets (Phase G)."""

from myalert_validate.validator import run_validation
from myalert_validate.models import ValidationConfig

__all__ = ["run_validation", "ValidationConfig"]
__version__ = "1.0.0"
