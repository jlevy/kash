import difflib
from io import BytesIO
from pathlib import Path

from funlog import abbreviate_arg
from patch_ng import PatchSet
from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger
from kash.model.items_model import Item, ItemRelations, ItemType
from kash.model.paths_model import StorePath
from kash.utils.errors import ContentError
from kash.utils.file_utils.file_formats_model import Format

log = get_logger(__name__)


# TODO: Support diffs of path lists as well, including renames and moves.


@dataclass(frozen=True)
class UnifiedDiff:
    """
    A unified diff along with names of the before and after content and a diffstat summary.
    """

    from_name: str
    to_name: str
    patch_text: str
    diffstat: str

    def __str__(self) -> str:
        return self.patch_text


def patch_set_to_str(patch_set: PatchSet) -> str:
    output = ""
    for p in patch_set.items:
        for headline in p.header:
            output += headline.decode().rstrip("\n") + "\n"
        output += "--- " + p.source.decode() + "\n"
        output += "+++ " + p.target.decode() + "\n"
        for h in p.hunks:
            output += "@@ -%d,%d +%d,%d @@%s\n" % (
                h.startsrc,
                h.linessrc,
                h.starttgt,
                h.linestgt,
                h.desc.decode(),
            )
            for line in h.text:
                output += line.decode()
    return output


def unified_diff(
    from_content: str | None,
    to_content: str | None,
    from_name: str = "before",
    to_name: str = "after",
) -> UnifiedDiff:
    """
    Generate a unified diff between two strings.
    """
    lines1 = from_content.splitlines() if from_content else []
    lines2 = to_content.splitlines() if to_content else []

    # Generate the diff text using difflib
    diff_lines = difflib.unified_diff(
        lines1,
        lines2,
        fromfile=from_name,
        tofile=to_name,
        lineterm="",
    )
    diff_text = "\n".join(diff_lines)

    patch_set = PatchSet(BytesIO(diff_text.encode("utf-8")))
    if patch_set.errors > 0:
        raise ContentError(
            f"Had {patch_set.errors} errors parsing diff of `{from_name}` and `{to_name}`: {abbreviate_arg(diff_text)}"
        )

    return UnifiedDiff(from_name, to_name, patch_set_to_str(patch_set), str(patch_set.diffstat()))


def unified_diff_files(from_file: str | Path, to_file: str | Path) -> UnifiedDiff:
    """
    Generate a unified diff between two files.
    """
    from_file, to_file = Path(from_file), Path(to_file)

    # Recognizable names for each file.
    from_name = from_file.name
    to_name = to_file.name
    if from_name == to_name:
        from_name = str(from_file)
        to_name = str(to_file)

    with open(from_file) as f1, open(to_file) as f2:
        content1 = f1.read()
        content2 = f2.read()

    return unified_diff(content1, content2, from_name, to_name)


def unified_diff_items(from_item: Item, to_item: Item, strict: bool = True) -> Item:
    """
    Generate a unified diff between two items. If `strict` is true, will raise
    an error if the items are of different formats.
    """
    if not from_item.body and not to_item.body:
        raise ContentError(f"No body to diff for {from_item} and {to_item}")
    if not from_item.store_path or not to_item.store_path:
        raise ContentError("No store path on items; save before diffing")
    diff_items = [item for item in [from_item, to_item] if item.format == Format.diff]
    if len(diff_items) == 1:
        raise ContentError(
            f"Cannot compare diffs to non-diffs: {from_item.format}, {to_item.format}"
        )
    if len(diff_items) > 0 or from_item.format != to_item.format:
        msg = f"Diffing items of incompatible format: {from_item.format}, {to_item.format}"
        if strict:
            raise ContentError(msg)
        else:
            log.warning("%s", msg)

    from_path, to_path = StorePath(from_item.store_path), StorePath(to_item.store_path)

    diff = unified_diff(from_item.body, to_item.body, str(from_path), str(to_path))

    return Item(
        type=ItemType.doc,
        title=f"Diff of {from_path} and {to_path}",
        format=Format.diff,
        relations=ItemRelations(diff_of=[from_path, to_path]),
        body=diff.patch_text,
    )
