from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from sidematter_format.sidematter_format import Sidematter

from kash.utils.common.url import Url, is_s3_url, parse_s3_url


def check_aws_cli() -> None:
    """
    Check if the AWS CLI is installed and available.
    """
    if shutil.which("aws") is None:
        raise RuntimeError(
            "AWS CLI not found in PATH. Please install 'awscli' and ensure 'aws' is available."
        )


def get_s3_parent_folder(url: Url) -> Url | None:
    """
    Get the parent folder of an S3 URL, or None if not an S3 URL.
    """
    if is_s3_url(url):
        s3_bucket, s3_key = parse_s3_url(url)
        s3_parent_folder = Path(s3_key).parent

        return Url(f"s3://{s3_bucket}/{s3_parent_folder}")

    else:
        return None


def s3_sync_to_folder(
    src_path: str | Path,
    s3_dest_parent: Url,
    *,
    include_sidematter: bool = False,
) -> list[Url]:
    """
    Sync a local file or directory to an S3 "parent" folder using the AWS CLI.
    Set `include_sidematter` to include sidematter files alongside the source files.

    Returns a list of S3 URLs that were the top-level sync targets:
    - For a single file: the file URL (and sidematter file/dir URLs if included).
    - For a directory: the destination parent prefix URL (non-recursive reporting).
    """

    src_path = Path(src_path)
    if not src_path.exists():
        raise ValueError(f"Source path does not exist: {src_path}")
    if not is_s3_url(s3_dest_parent):
        raise ValueError(f"Destination must be an s3:// URL: {s3_dest_parent}")

    check_aws_cli()

    dest_prefix = str(s3_dest_parent).rstrip("/") + "/"
    targets: list[Url] = []

    if src_path.is_file():
        # Build the list of paths to sync using Sidematter's resolved path_list if requested.
        sync_paths: list[Path]
        if include_sidematter:
            resolved = Sidematter(src_path).resolve(parse_meta=False, use_frontmatter=False)
            sync_paths = resolved.path_list
        else:
            sync_paths = [src_path]

        for p in sync_paths:
            if p.is_file():
                # Use sync with include/exclude to leverage default short-circuiting
                subprocess.run(
                    [
                        "aws",
                        "s3",
                        "sync",
                        str(p.parent),
                        dest_prefix,
                        "--exclude",
                        "*",
                        "--include",
                        p.name,
                    ],
                    check=True,
                )
                targets.append(Url(dest_prefix + p.name))
            elif p.is_dir():
                dest_dir = dest_prefix + p.name + "/"
                subprocess.run(["aws", "s3", "sync", str(p), dest_dir], check=True)
                targets.append(Url(dest_dir))

        return targets
    else:
        # Directory mode: sync whole directory.
        subprocess.run(
            [
                "aws",
                "s3",
                "sync",
                str(src_path),
                dest_prefix,
            ],
            check=True,
        )
        targets.append(Url(dest_prefix))
        return targets
