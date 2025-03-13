from pathlib import Path

from kash.exec import import_action_subdirs

# This hook can be used for auto-registering actions from any module.
import_action_subdirs(["core_actions"], __package__, Path(__file__).parent)
