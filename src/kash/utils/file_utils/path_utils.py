from pathlib import Path


def common_path(*paths: Path) -> Path:
    """
    Resolve all paths and find the longest common path that all paths are relative to.
    Result is absolute. If input is empty or paths have no common parent, returns
    Path("/").
    """
    if not paths:
        return Path("/")
    # Start with the first path as the candidate common path.
    # Then loop throu the rest.
    common = paths[0].resolve()
    for path in paths[1:]:
        path = path.resolve()
        while common != Path("/") and not path.is_relative_to(common):
            common = common.parent

        if common == Path("/"):
            break

    return common


def common_parent_dir(*paths: Path) -> Path:
    """
    Resolve all paths and find the longest common parent directory that all paths are
    relative to. Result is absolute. If input is empty or paths have no common parent,
    returns Path("/").
    """
    common = common_path(*paths)
    if common.exists() and not common.is_dir():
        return common.parent
    else:
        return common
