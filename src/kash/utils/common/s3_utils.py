from __future__ import annotations

import os
import shutil
import subprocess
from logging import getLogger
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from sidematter_format.sidematter_format import Sidematter
from strif import abbrev_str

from kash.utils.common.url import Url, is_s3_url, parse_s3_url

log = getLogger(__name__)


def check_aws_cli() -> None:
    """
    Check if the AWS CLI is installed and available.
    """
    if shutil.which("aws") is None:
        raise RuntimeError(
            "AWS CLI not found in PATH. Please install 'awscli' and ensure 'aws' is available."
        )


def run_aws_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """
    Run an AWS CLI command and capture output.
    Raises a RuntimeError with stdout/stderr on failure.
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=os.environ,
    )

    if result.returncode != 0:
        # Build a detailed error message
        error_parts = [f"AWS command failed with exit code {result.returncode}"]
        error_parts.append(f"Command: {' '.join(cmd)}")

        if result.stdout:
            error_parts.append(f"stdout: {result.stdout}")
        if result.stderr:
            error_parts.append(f"stderr: {result.stderr}")

        raise RuntimeError("\n".join(error_parts))

    return result


def reload_aws_env_vars() -> None:
    """
    Fresh reload of AWS env vars from .env.local.
    """

    def aws_creds() -> set[tuple[str, str]]:
        return {(k, abbrev_str(v, 5)) for k, v in os.environ.items() if k.startswith("AWS_")}

    if len(aws_creds()) == 0:
        dotenv_path = find_dotenv(".env.local", usecwd=True) or find_dotenv(".env", usecwd=True)
        load_dotenv(dotenv_path, override=True)
        if len(aws_creds()) > 0:
            log.info(
                "Loaded %s, found AWS credentials: %s",
                dotenv_path,
                aws_creds(),
            )
        else:
            log.warning("No AWS credentials found in env or .env files")


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
    reload_aws_env_vars()

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
                run_aws_command(
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
                    ]
                )
                targets.append(Url(dest_prefix + p.name))
            elif p.is_dir():
                dest_dir = dest_prefix + p.name + "/"
                run_aws_command(["aws", "s3", "sync", str(p), dest_dir])
                targets.append(Url(dest_dir))

        return targets
    else:
        # Directory mode: sync whole directory.
        run_aws_command(
            [
                "aws",
                "s3",
                "sync",
                str(src_path),
                dest_prefix,
            ]
        )
        targets.append(Url(dest_prefix))
        return targets


def s3_download_file(s3_url: Url, target_path: str | Path) -> None:
    """
    Download a file from S3 to a local path using the AWS CLI.

    Args:
        s3_url: The S3 URL to download from (s3://bucket/path/to/file)
        target_path: The local path to save the file to
    """
    reload_aws_env_vars()

    if not is_s3_url(s3_url):
        raise ValueError(f"Source must be an s3:// URL: {s3_url}")

    check_aws_cli()

    target_path = Path(target_path)

    # Use aws s3 cp to download the file
    run_aws_command(
        [
            "aws",
            "s3",
            "cp",
            str(s3_url),
            str(target_path),
        ]
    )
