import importlib
import logging
import pkgutil
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

log = logging.getLogger(__name__)

Tallies: TypeAlias = dict[str, int]


def import_subdirs(
    parent_package_name: str,
    parent_dir: Path,
    subdir_names: list[str],
    tallies: Tallies | None = None,
):
    """
    Import all files in the given subdirectories of a single parent directory.
    """
    if tallies is None:
        tallies = {}

    for subdir_name in subdir_names:
        full_path = parent_dir / subdir_name
        if not full_path.is_dir():
            raise FileNotFoundError(f"Subdirectory not found: {full_path}")

        package_name = f"{parent_package_name}.{subdir_name}"
        for _module_finder, module_name, _is_pkg in pkgutil.iter_modules(path=[str(full_path)]):
            importlib.import_module(f"{package_name}.{module_name}")  # Propagate import errors
            tallies[package_name] = tallies.get(package_name, 0) + 1

    return tallies


def import_namespace_modules(namespace: str) -> dict[str, types.ModuleType]:
    """
    Find and import all modules or packages within a namespace package.
    Returns a dictionary mapping module names to their imported module objects.
    """
    importlib.import_module(namespace)  # Propagate import errors

    # Get the package to access its __path__
    package = sys.modules.get(namespace)
    if not package or not hasattr(package, "__path__"):
        raise ImportError(f"`{namespace}` is not a package or namespace package")

    log.info(f"Discovering modules in `{namespace}` namespace, searching: {package.__path__}")

    # Iterate through all modules in the namespace package
    modules = {}
    for _finder, module_name, _ispkg in pkgutil.iter_modules(package.__path__, f"{namespace}."):
        module = importlib.import_module(module_name)  # Propagate import errors
        log.info(f"Imported module: {module_name} from {module.__file__}")
        modules[module_name] = module

    log.info(f"Imported {len(modules)} modules from namespace `{namespace}`")
    return modules


def recursive_reload(
    package: types.ModuleType, filter_func: Callable[[str], bool] | None = None
) -> list[str]:
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
