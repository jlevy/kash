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


def import_recursive(
    parent_package_name: str,
    parent_dir: Path,
    resource_names: list[str] | None = None,
    tallies: Tallies | None = None,
):
    """
    Import modules from subdirectories or individual Python modules within a parent package.

    Each resource in `resource_names` can be:
    - A directory name (all modules within it will be imported)
    - A module name with or without '.py' extension (a single module will be imported)
    - "." to import all modules in the parent_dir

    If `resource_names` is `None`, imports all modules directly in parent_dir.

    Simply a convenience wrapper for `importlib.import_module` and
    `pkgutil.iter_modules` to iterate over all modules in the subdirectories.

    If `tallies` is provided, it will be updated with the number of modules imported
    for each package.
    """
    if tallies is None:
        tallies = {}
    if not resource_names:
        resource_names = ["."]

    for name in resource_names:
        if name == ".":
            full_path = parent_dir
            package_name = parent_package_name
        else:
            full_path = parent_dir / name
            package_name = f"{parent_package_name}.{name}"

        # Check if it's a directory
        if full_path.is_dir():
            # Import all modules in the directory
            for _, module_name, _ in pkgutil.iter_modules(path=[str(full_path)]):
                importlib.import_module(f"{package_name}.{module_name}")
                tallies[package_name] = tallies.get(package_name, 0) + 1
        else:
            # Not a directory, try as a module file
            module_path = full_path
            module_name = name

            # Handle with or without .py extension
            if not module_path.is_file() and module_path.suffix != ".py":
                module_path = parent_dir / f"{name}.py"
                module_name = name
            elif module_path.suffix == ".py":
                module_name = module_path.stem

            if module_path.is_file() and module_name != "__init__":
                importlib.import_module(f"{parent_package_name}.{module_name}")
                tallies[parent_package_name] = tallies.get(parent_package_name, 0) + 1
            else:
                raise FileNotFoundError(f"Path not found or not importable: {full_path}")

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
