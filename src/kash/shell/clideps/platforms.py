import platform
from enum import StrEnum


class Platform(StrEnum):
    Darwin = "Darwin"
    Linux = "Linux"
    Windows = "Windows"


PLATFORM = Platform(platform.system())
