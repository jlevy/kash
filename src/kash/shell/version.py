import subprocess
from importlib import metadata

PACKAGE_NAME = "kash-shell"


def get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not read git hash: {e}")
        raise e


def get_version():
    # If desired, could also fall back with git hash.
    return metadata.version(PACKAGE_NAME)


def get_version_tag():
    """Version number with a leading 'v', as typically used in git tags."""
    return f"v{get_version()}"


def get_full_version_name(with_kits: bool = True):
    version_items = [f"{PACKAGE_NAME} {get_version_tag()}"]
    if with_kits:
        from kash.actions import get_loaded_kits

        kits = get_loaded_kits()
        for kit in kits.values():
            if kit.version:
                version_items.append(f"{kit.distribution_name} v{kit.version}")

    return ", ".join(version_items)


if __name__ == "__main__":
    print(get_version_tag())
