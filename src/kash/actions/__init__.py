from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from strif import AtomicVar

from kash.config.logger import get_logger
from kash.config.settings import APP_NAME
from kash.exec import import_and_register
from kash.utils.common.import_utils import import_namespace_modules

log = get_logger(__name__)

import_and_register(__package__, Path(__file__).parent, ["core", "meta"])


@dataclass(frozen=True)
class Kit:
    module_name: str
    distribution_name: str
    full_module_name: str
    path: Path | None
    version: str | None = None


_kits: AtomicVar[dict[str, Kit]] = AtomicVar(initial_value={})


def get_loaded_kits() -> dict[str, Kit]:
    """
    Get all kits (modules within `kash.kits`) that have been loaded.
    """
    return _kits.copy()


def get_kit_distribution_name(module_name: str) -> str | None:
    """
    Guess the distribution name for a kit module using naming conventions.
    Assumes kits follow patterns like:
    - kash.kits.example_kit -> kash-example-kit
    """
    if not module_name.startswith("kash.kits."):
        return None

    kit_name = module_name.removeprefix("kash.kits.")

    # Try common naming patterns
    candidates = [
        f"kash-{kit_name}",
        f"kash-{kit_name.replace('_', '-')}",
    ]

    for candidate in candidates:
        try:
            metadata.version(candidate)
            return candidate
        except metadata.PackageNotFoundError:
            continue

    return None


def get_distribution_version(module_name: str) -> str | None:
    """
    Get the version of a module that can be used with `metadata.version()`.
    """
    try:
        dist_name = get_kit_distribution_name(module_name)
        return metadata.version(dist_name) if dist_name else None
    except Exception:
        return None


def load_kits() -> dict[str, Kit]:
    """
    Import all kits (modules within `kash.kits`) by inspecting the namespace.
    """
    kits_namespace = f"{APP_NAME}.kits"
    new_kits = {}
    try:
        imported = import_namespace_modules(kits_namespace)
        for module_name, module in imported.items():
            dist_name = get_kit_distribution_name(module.__name__) or module.__name__

            new_kits[module_name] = Kit(
                module_name=module_name,
                distribution_name=dist_name,
                full_module_name=module.__name__,
                path=Path(module.__file__) if module.__file__ else None,
                version=metadata.version(dist_name),
            )
    except ImportError:
        log.info("No kits found in namespace `%s`", kits_namespace)

    _kits.update(lambda kits: {**kits, **new_kits})

    return new_kits


load_kits()
