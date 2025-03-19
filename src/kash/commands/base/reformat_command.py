import os

from prettyfmt import fmt_lines

from kash.commands.base.basic_file_commands import trash
from kash.commands.workspace.selection_commands import select
from kash.config.logger import get_logger
from kash.exec import assemble_path_args, kash_command, resolvable_paths
from kash.exec_model.shell_model import ShellResult
from kash.shell.output.shell_output import print_status
from kash.text_handling.doc_normalization import normalize_text_file
from kash.utils.common.format_utils import fmt_loc
from kash.utils.file_utils.filename_parsing import join_filename, split_filename

log = get_logger(__name__)


@kash_command
def reformat(*paths: str, inplace: bool = False) -> ShellResult:
    """
    Format text, Markdown, or HTML according to kash conventions.

    TODO: Also handle JSON and YAML.

    :param inplace: Overwrite the original file. Otherwise save to a new
    file with `_formatted` appended to the original name.
    """
    resolved_paths = assemble_path_args(*paths)
    final_paths = []

    for path in resolved_paths:
        target_path = None
        dirname, name, item_type, ext = split_filename(path)
        new_name = f"{name}_formatted"
        target_path = join_filename(dirname, new_name, item_type, ext)

        normalize_text_file(path, target_path=target_path)
        if inplace:
            trash(path)
            os.rename(target_path, path)
            print_status("Formatted:\n%s", fmt_lines([fmt_loc(path)]))
            final_paths.append(path)
        else:
            print_status(
                "Formatted:\n%s",
                fmt_lines([f"{fmt_loc(path)} -> {fmt_loc(target_path)}"]),
            )
            final_paths.append(target_path)

    resolvable = resolvable_paths(final_paths)
    if resolvable:
        select(*resolvable)

    return ShellResult(show_selection=len(resolvable) > 0)
