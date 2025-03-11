import subprocess
from importlib import metadata

PACKAGE_NAME = "kash_shell"


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


def get_version_name():
    return f"v{get_version()}"


if __name__ == "__main__":
    print(get_version_name())
