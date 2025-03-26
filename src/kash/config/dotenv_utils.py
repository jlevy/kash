import os

from dotenv import find_dotenv, load_dotenv


def find_load_dotenv(override: bool = True) -> list[str]:
    """
    Find and load .env files.
    """
    paths = []
    dotenv_path = find_dotenv(filename=".env", usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=override)
        paths.append(dotenv_path)
    dotenv_path = find_dotenv(filename=".env.local", usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=override)
        paths.append(dotenv_path)
    return paths


def env_var_is_set(key: str, min_length: int = 10, forbidden_str: str = "changeme") -> bool:
    """
    Check if an environment variable is set and plausible (not a dummy or empty value).
    """
    value = os.environ.get(key, None)
    return bool(value and len(value.strip()) > min_length and forbidden_str not in value)
