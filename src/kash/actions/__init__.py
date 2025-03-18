from dataclasses import dataclass
from pathlib import Path

from kash.config.logger import get_logger
from kash.config.settings import APP_NAME
from kash.exec import import_action_subdirs
from kash.utils.common.atomic_var import AtomicVar
from kash.utils.common.import_utils import import_namespace_modules

log = get_logger(__name__)

# This hook can be used for auto-registering actions from any module.
import_action_subdirs(["core", "meta"], __package__, Path(__file__).parent)


@dataclass(frozen=True)
class Kit:
    name: str
    full_module_name: str
    path: Path | None


_kits: AtomicVar[dict[str, Kit]] = AtomicVar(initial_value={})


def get_loaded_kits() -> dict[str, Kit]:
    """
    Get all kits (modules within `kash.kits`) that have been loaded.
    """
    return _kits.copy()


def load_kits() -> dict[str, Kit]:
    """
    Import all kits (modules within `kash.kits`) by inspecting the namespace.
    """
    kits_namespace = f"{APP_NAME}.kits"
    new_kits = {}
    try:
        imported = import_namespace_modules(kits_namespace)
        for name, module in imported.items():
            new_kits[name] = Kit(
                name,
                module.__name__,
                Path(module.__file__) if module.__file__ else None,
            )
    except ImportError:
        log.info("No kits found in namespace `%s`", kits_namespace)

    _kits.update(lambda kits: {**kits, **new_kits})

    return new_kits


load_kits()
