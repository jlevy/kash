import importlib
import pkgutil
import sys
import types
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypeAlias


Tallies: TypeAlias = Dict[str, int]


def _import_all_files(path: Path, base_package: str, tallies: Optional[Tallies] = None) -> Tallies:
    if tallies is None:
        tallies = {}

    current_package = __name__
    for _module_finder, module_name, _is_pkg in pkgutil.iter_modules(path=[str(path)]):
        importlib.import_module(f"{base_package}.{module_name}", current_package)
        tallies[base_package] = tallies.get(base_package, 0) + 1

    return tallies


def import_subdirs(
    parent_package_name: str,
    parent_dir: Path,
    subdir_names: List[str],
    tallies: Optional[Tallies] = None,
):
    if tallies is None:
        tallies = {}

    for subdir_name in subdir_names:
        full_path = parent_dir / subdir_name
        if full_path.is_dir():
            package_name = f"{parent_package_name}.{subdir_name}"
            _import_all_files(full_path, package_name, tallies)

    return tallies


def recursive_reload(
    package: types.ModuleType, filter_func: Optional[Callable[[str], bool]] = None
) -> List[str]:
    """
    Recursively reload all modules in the given package that match the filter function.
    Returns a list of module names that were reloaded.

    :param filter_func: A function that takes a module name and returns True if the
        module should be reloaded.
    """
    package_name = package.__name__
    modules = {
        name: module
        for name, module in sys.modules.items()
        if (
            (name == package_name or name.startswith(package_name + "."))
            and isinstance(module, types.ModuleType)
            and (filter_func is None or filter_func(name))
        )
    }
    module_names = sorted(modules.keys(), key=lambda name: name.count("."), reverse=True)
    for name in module_names:
        importlib.reload(modules[name])

    return module_names
