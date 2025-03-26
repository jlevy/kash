"""
The core classes for modeling kash's framework.

We include essential logic here but try to keep logic and dependencies minimal.
"""

# flake8: noqa: F401

from kash.exec_model.args_model import (
    ANY_ARGS,
    NO_ARGS,
    ONE_ARG,
    ONE_OR_MORE_ARGS,
    ONE_OR_NO_ARGS,
    TWO_ARGS,
    TWO_OR_MORE_ARGS,
    ArgCount,
    CommandArg,
)
from kash.exec_model.commands_model import Command, CommentedCommand
from kash.exec_model.script_model import BareComment, Script
from kash.exec_model.shell_model import ShellResult
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
from kash.model.compound_actions_model import ComboAction, SequenceAction, look_up_actions
from kash.model.graph_model import GraphData, Link, Node
from kash.model.items_model import (
    SLUG_MAX_LEN,
    UNTITLED,
    IdType,
    Item,
    ItemId,
    ItemRelations,
    ItemType,
    State,
)
from kash.model.media_model import (
    SERVICE_APPLE_PODCASTS,
    SERVICE_VIMEO,
    SERVICE_YOUTUBE,
    HeatmapValue,
    MediaMetadata,
    MediaService,
    MediaUrlType,
)
from kash.model.params_model import (
    ALL_COMMON_PARAMS,
    COMMON_ACTION_PARAMS,
    GLOBAL_PARAMS,
    RUNTIME_ACTION_PARAMS,
    USER_SETTABLE_PARAMS,
    Param,
    ParamDeclarations,
    RawParamValues,
    TypedParamValues,
    common_param,
    common_params,
)
from kash.model.paths_model import StorePath
from kash.model.preconditions_model import Precondition
from kash.utils.common.format_utils import fmt_loc
from kash.utils.file_utils.file_formats_model import FileExt, Format, MediaType
