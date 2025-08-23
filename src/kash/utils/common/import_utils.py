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


def _import_modules_from_package(
    package: types.ModuleType,
    package_name: str,
    max_depth: int = 1,
    include_private: bool = True,
    current_depth: int = 0,
    imported_modules: dict[str, types.ModuleType] | None = None,
) -> dict[str, types.ModuleType]:
    """
    Internal helper to recursively import modules from a package.

    Args:
        package: The package module to import from
        package_name: The fully qualified name of the package
        max_depth: Maximum recursion depth (1 = direct children only)
        include_private: Whether to import private modules (starting with _)
        current_depth: Current recursion depth (internal use)
        imported_modules: Dictionary to accumulate imported modules

    Returns:
        Dictionary mapping module names to their imported module objects
    """
    if imported_modules is None:
        imported_modules = {}

    if current_depth >= max_depth:
        return imported_modules

    # Get the module's __path__ if it's a package
    if not hasattr(package, "__path__"):
        return imported_modules

    try:
        for _finder, module_name, ispkg in pkgutil.iter_modules(
            package.__path__, f"{package_name}."
        ):
            # Skip private modules unless requested
            if not include_private and module_name.split(".")[-1].startswith("_"):
                continue

            # Skip test modules - they often have special import requirements
            # and aren't needed for warming the import cache
            module_parts = module_name.split(".")
            if any(
                part in ("tests", "test", "testing", "_test", "_tests") for part in module_parts
            ):
                continue

            # Skip already imported modules
            if module_name in imported_modules:
                continue

            try:
                module = importlib.import_module(module_name)
                imported_modules[module_name] = module

                # Recursively import submodules if it's a package
                if ispkg and current_depth + 1 < max_depth:
                    _import_modules_from_package(
                        module,
                        module_name,
                        max_depth=max_depth,
                        include_private=include_private,
                        current_depth=current_depth + 1,
                        imported_modules=imported_modules,
                    )

            except Exception as e:
                # Handle various import failures gracefully
                # This includes ImportError, pytest.Skipped, and other exceptions
                error_type = type(e).__name__
                if error_type not in ("ImportError", "AttributeError", "TypeError"):
                    log.debug(f"  Skipped {module_name}: {error_type}: {e}")
                # Don't log common/expected import errors to reduce noise

    except Exception as e:
        log.warning(f"Error iterating modules in {package_name}: {e}")

    return imported_modules


def import_namespace_modules(namespace: str) -> dict[str, types.ModuleType]:
    """
    Find and import all modules or packages within a namespace package.
    Returns a dictionary mapping module names to their imported module objects.
    """
    # Import the main module first
    main_module = importlib.import_module(namespace)  # Propagate import errors

    # Get the package to access its __path__
    if not hasattr(main_module, "__path__"):
        raise ImportError(f"`{namespace}` is not a package or namespace package")

    log.info(f"Discovering modules in `{namespace}` namespace, searching: {main_module.__path__}")

    # Use the common helper with depth=1 (no recursion) and include_private=True
    modules = _import_modules_from_package(
        main_module, namespace, max_depth=1, include_private=True
    )

    # Add the main module itself
    modules[namespace] = main_module

    log.info(f"Imported {len(modules)} modules from namespace `{namespace}`")
    return modules


def recursive_reload(
    package: types.ModuleType, filter_func: Callable[[str], bool] | None = None
) -> list[str]:
    """
    Recursively reload all modules in the given package that match the filter function.
    Returns a list of module names that were reloaded.

    Args:
        package: The package to reload.
        filter_func: A function that takes a module name and returns True if the
            module should be reloaded.

    Returns:
        List of module names that were reloaded.
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


def warm_import_library(
    library_name: str, max_depth: int = 3, include_private: bool = False
) -> dict[str, types.ModuleType]:
    """
    Recursively import all submodules of a library to warm the import cache.
    This is useful for servers where you want to pay the import cost upfront
    rather than during request handling.

    Args:
        library_name: Name of the library to import (e.g., 'litellm', 'openai')
        max_depth: Maximum depth to recurse into submodules
        include_private: Whether to import private modules (starting with _)

    Returns:
        Dictionary mapping module names to their imported module objects
    """
    try:
        # Import the main module first
        main_module = importlib.import_module(library_name)

        # Use the common helper for recursive imports
        imported_modules = _import_modules_from_package(
            main_module, library_name, max_depth=max_depth, include_private=include_private
        )

        # Add the main module itself
        imported_modules[library_name] = main_module

    except ImportError as e:
        log.warning(f"Could not import {library_name}: {e}")
        return {}

    log.info(f"Warmed {len(imported_modules)} modules from {library_name}")

    return imported_modules
