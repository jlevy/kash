# This file is part of the namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Canonical public API imports.
# These provide convenient top-level access to the most commonly used symbols.
# All existing deep import paths (e.g. `from kash.model.items_model import Item`)
# remain valid and unchanged.

# Core model types
from kash.model.items_model import Item, ItemType  # noqa: F401
from kash.model.actions_model import Action, ActionInput, ActionResult, LLMOptions  # noqa: F401
from kash.model.params_model import Param, common_param, common_params  # noqa: F401
from kash.model.paths_model import StorePath  # noqa: F401
from kash.model.preconditions_model import Precondition  # noqa: F401
from kash.utils.file_utils.file_formats_model import Format, FileExt  # noqa: F401

# Execution decorators and helpers
from kash.exec.action_decorators import kash_action, kash_action_class  # noqa: F401
from kash.exec.precondition_registry import kash_precondition  # noqa: F401
from kash.exec.command_registry import kash_command  # noqa: F401
from kash.exec.importing import import_and_register  # noqa: F401

# LLM utilities
from kash.llm_utils.llm_names import LLMName  # noqa: F401
from kash.llm_utils.llm_messages import Message, MessageTemplate  # noqa: F401

# Standalone runner
from kash.run import kash_init, kash_run  # noqa: F401

# Errors
from kash.utils.errors import InvalidInput, InvalidOutput, ContentError, ApiResultError  # noqa: F401

__all__ = [
    # Core model
    "Item",
    "ItemType",
    "Action",
    "ActionInput",
    "ActionResult",
    "LLMOptions",
    "Param",
    "common_param",
    "common_params",
    "StorePath",
    "Precondition",
    "Format",
    "FileExt",
    # Execution
    "kash_action",
    "kash_action_class",
    "kash_precondition",
    "kash_command",
    "import_and_register",
    # LLM
    "LLMName",
    "Message",
    "MessageTemplate",
    # Standalone runner
    "kash_init",
    "kash_run",
    # Errors
    "InvalidInput",
    "InvalidOutput",
    "ContentError",
    "ApiResultError",
]
