from pathlib import Path
from typing import Dict, Optional

from funlog import log_calls

from kash.config.logger import get_logger
from kash.util.import_utils import import_subdirs
from kash.util.type_utils import not_none

log = get_logger(__name__)

BASE_DIRS = ["core_actions"]
COMPOUND_DIRS = []


@log_calls(level="info", show_returns_only=True, show_return_value=False)
def import_actions(
    base_only: bool = False, tallies: Optional[Dict[str, int]] = None
) -> Dict[str, int]:
    # Allow bootstrapping base actions before compound actions that may depend on them.
    package_name = not_none(__package__)
    parent_dir = Path(__file__).parent

    if tallies is None:
        tallies = {}

    import_subdirs(package_name, parent_dir, BASE_DIRS, tallies)
    if not base_only:
        import_subdirs(package_name, parent_dir, COMPOUND_DIRS, tallies)

    return tallies
