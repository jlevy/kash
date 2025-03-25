# Import all command modules to ensure commands are registered.

import kash.commands.base.basic_file_commands  # noqa: F401
import kash.commands.base.browser_commands  # noqa: F401
import kash.commands.base.debug_commands  # noqa: F401
import kash.commands.base.diff_commands  # noqa: F401
import kash.commands.base.files_command  # noqa: F401
import kash.commands.base.general_commands  # noqa: F401
import kash.commands.base.logs_commands  # noqa: F401
import kash.commands.base.model_commands  # noqa: F401
import kash.commands.base.reformat_command  # noqa: F401
import kash.commands.base.search_command  # noqa: F401
import kash.commands.base.show_command  # noqa: F401
import kash.commands.extras.utils_commands  # noqa: F401
import kash.commands.help.assistant_commands  # noqa: F401  # noqa: F401
import kash.commands.help.doc_commands  # noqa: F401
import kash.commands.help.help_commands  # noqa: F401
import kash.commands.workspace.selection_commands  # noqa: F401
import kash.commands.workspace.workspace_commands  # noqa: F401
import kash.local_server.local_server_commands  # noqa: F401
import kash.mcp.mcp_server_commands  # noqa: F401
