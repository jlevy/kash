"""
Common hierarchy of error types. These inherit from standard errors like
ValueError and FileExistsError but are more fine-grained.
"""


class KashRuntimeError(ValueError):
    """Base class for kash runtime errors."""

    pass


class UnexpectedError(KashRuntimeError):
    """For unexpected errors or runtime check failures."""

    pass


class ApiResultError(KashRuntimeError):
    """Raised when an API doesn't behave as expected."""

    pass


class SelfExplanatoryError(KashRuntimeError):
    """Common errors that arise from 'normal' problems that are largely self-explanatory,
    i.e., no stack trace should be necessary when reporting to the user."""

    pass


class InvalidInput(SelfExplanatoryError):
    """Raised when the wrong kind of input is given to an action or command."""

    pass


class MissingInput(InvalidInput):
    """Raised when an expected input is missing."""

    pass


class InvalidParamName(InvalidInput):
    """Raised when a parameter is invalid."""

    def __init__(self, param_name: str):
        super().__init__(f"Invalid parameter: {repr(param_name)}")


class InvalidDefinition(SelfExplanatoryError):
    """Raised when a command or action definition is invalid."""

    pass


class InvalidOutput(SelfExplanatoryError):
    """Raised when an action returns invalid output."""

    pass


class NoMatch(InvalidInput):
    """Raised when a match is not found to a search or precondition."""

    pass


class FileExists(InvalidInput, FileExistsError):
    """Raised when a file already exists."""

    pass


class FileNotFound(InvalidInput, FileNotFoundError):
    """Raised when a file is not found."""

    pass


class InvalidFilename(InvalidInput):
    """Raised when a filename is invalid."""

    pass


class InvalidCommand(InvalidInput):
    """Raised when a command is not valid."""

    pass


class InvalidOperation(InvalidInput):
    """Raised when an operation can't be performed."""

    pass


class InvalidState(SelfExplanatoryError):
    """Raised when the store or other system state is not in a valid for an operation."""

    pass


class SetupError(SelfExplanatoryError):
    """Raised when a package is not installed or something in the environment
    isn't set up right."""

    pass


class SkippableError(SelfExplanatoryError):
    """Errors that are skippable and shouldn't abort the entire operation."""

    pass


class ContentError(SkippableError):
    """Raised when content is not appropriate for an operation."""

    pass


class UnrecognizedFileFormat(SkippableError):
    """Raised when a file has an unrecognized format."""

    pass


class PreconditionFailure(ContentError):
    """Raised when content is not suitable for the requested operation."""

    pass


class FileFormatError(ContentError):
    """Raised when a file's content format is invalid."""

    pass


def _nonfatal_exceptions() -> tuple[type[Exception], ...]:
    exceptions: list[type[Exception]] = [SelfExplanatoryError, FileNotFoundError, IOError]
    try:
        from xonsh.tools import XonshError

        exceptions.append(XonshError)
    except ImportError:
        pass

    try:
        import litellm

        exceptions.append(litellm.exceptions.APIError)
    except ImportError:
        pass

    try:
        import yt_dlp

        exceptions.append(yt_dlp.utils.DownloadError)
    except ImportError:
        pass

    return tuple(exceptions)


NONFATAL_EXCEPTIONS = _nonfatal_exceptions()
"""Exceptions that are not fatal and usually don't merit a full stack trace."""


def is_fatal(exception: Exception) -> bool:
    for e in NONFATAL_EXCEPTIONS:
        if isinstance(exception, e):
            return False
    return True
