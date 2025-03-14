import warnings


def filter_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*deprecated.*")
    warnings.filterwarnings("ignore", message=".*Deprecation.*")
    warnings.filterwarnings("ignore", message=".*PydanticDeprecatedSince20.*")
    warnings.filterwarnings("ignore", module="pydub")
    warnings.filterwarnings("ignore", module="pydantic")
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="xonsh.tools")


filter_warnings()
