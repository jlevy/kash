"""
The core classes for modeling kash's framework.

We include essential logic here but try to keep logic and dependencies minimal.
"""

# flake8: noqa: F401

from kash.exec_model.args_model import (
    ANY_ARGS,
    ArgCount,
    CommandArg,
    NO_ARGS,
    ONE_ARG,
    ONE_OR_MORE_ARGS,
    ONE_OR_NO_ARGS,
    TWO_ARGS,
    TWO_OR_MORE_ARGS,
)
from kash.exec_model.commands_model import Command, CommentedCommand
from kash.exec_model.script_model import BareComment, Script
from kash.exec_model.shell_model import ShellResult

from kash.file_tools.file_formats_model import FileExt, Format, MediaType
from kash.llm_tools.llm_messages import Message, MessageTemplate
from kash.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
    ExecContext,
    LLMOptions,
    PathOp,
    PathOpType,
    PerItemAction,
    TitleTemplate,
)
from kash.model.compound_actions_model import ComboAction, look_up_actions, SequenceAction
from kash.model.graph_model import GraphData, Link, Node
from kash.model.items_model import (
    IdType,
    Item,
    ItemId,
    ItemRelations,
    ItemType,
    SLUG_MAX_LEN,
    State,
    UNTITLED,
)
from kash.model.language_models import DEFAULT_EMBEDDING_MODEL, EmbeddingModel, LLM
from kash.model.media_model import (
    HeatmapValue,
    MediaMetadata,
    MediaService,
    MediaUrlType,
    SERVICE_APPLE_PODCASTS,
    SERVICE_VIMEO,
    SERVICE_YOUTUBE,
)
from kash.model.params_model import (
    ALL_COMMON_PARAMS,
    COMMON_ACTION_PARAMS,
    common_param,
    common_params,
    GLOBAL_PARAMS,
    Param,
    ParamDeclarations,
    RawParamValues,
    RUNTIME_ACTION_PARAMS,
    TypedParamValues,
    USER_SETTABLE_PARAMS,
)
from kash.model.paths_model import StorePath
from kash.model.preconditions_model import Precondition, precondition
from kash.util.format_utils import fmt_loc
