from pathlib import Path

from kash.config.logger import get_logger
from kash.config.settings import APP_NAME
from kash.exec import import_action_subdirs
from kash.util.import_utils import import_namespace_modules

log = get_logger(__name__)

# This hook can be used for auto-registering actions from any module.
import_action_subdirs(["core", "meta"], __package__, Path(__file__).parent)


# Import all kits, if available.
kits_namespace = f"{APP_NAME}.kits"
try:
    import_namespace_modules(kits_namespace)
except ImportError:
    log.info("No kits found in namespace `%s`", kits_namespace)
