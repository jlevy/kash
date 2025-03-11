# Import all command modules to ensure commands are registered.

import kash.commands.base_commands.basic_file_commands  # noqa: F401
import kash.commands.base_commands.browser_commands  # noqa: F401
import kash.commands.base_commands.debug_commands  # noqa: F401
import kash.commands.base_commands.diff_commands  # noqa: F401
import kash.commands.base_commands.files_command  # noqa: F401
import kash.commands.base_commands.general_commands  # noqa: F401
import kash.commands.base_commands.global_state_commands  # noqa: F401
import kash.commands.base_commands.logs_commands  # noqa: F401
import kash.commands.base_commands.reformat_command  # noqa: F401
import kash.commands.base_commands.search_command  # noqa: F401
import kash.commands.base_commands.show_command  # noqa: F401
import kash.commands.help_commands.assistant_commands  # noqa: F401  # noqa: F401
import kash.commands.help_commands.doc_commands  # noqa: F401
import kash.commands.help_commands.help_commands  # noqa: F401
import kash.commands.workspace_commands.selection_commands  # noqa: F401
import kash.commands.workspace_commands.workspace_commands  # noqa: F401
import kash.local_server.local_server_commands  # noqa: F401
import kash.mcp.mcp_server_commands  # noqa: F401
