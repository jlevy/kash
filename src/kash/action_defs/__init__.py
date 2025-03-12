from pathlib import Path
from typing import Optional

from kash.util.import_utils import import_subdirs, Tallies
from kash.util.type_utils import not_none


def import_core_actions(tallies: Optional[Tallies] = None):
    package_name = not_none(__package__)
    parent_dir = Path(__file__).parent

    return import_subdirs(package_name, parent_dir, ["core_actions"], tallies)
