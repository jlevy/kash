from kash.utils.file_utils.file_formats_model import Format

# TODO: Consider adding more categories, either aligning with eza or seti-ui/VSCode:
# https://github.com/jesseweed/seti-ui/blob/master/styles/components/icons/mapping.less
# https://github.com/eza-community/eza/blob/main/src/info/filetype.rs
# https://github.com/eza-community/eza/pull/1349
#
# class FileCategory(Enum):
#     image = "image"
#     video = "video"
#     music = "music"
#     lossless = "lossless"
#
#     crypto = "crypto"
#     """Cryptographic files and keys"""
#
#     text = "text"
#     """Readable text"""
#     document = "document"
#     """Non-plaintext documents"""
#     compressed = "compressed"
#     """Compressed files"""
#     temp = "temp"
#     """Temporary files"""
#     compiled = "compiled"
#     """Compiled files"""
#     build = "build"
#     """Build files"""
#     source = "source"
#     """Source code"""
#     text_data = "text_data"
#     """Readable data"""
#     binary_data = "binary_data"
#     """Binary data"""
#     unknown = "unknown"
#     """Everything else"""


def color_for_format(format: Format | None) -> str:
    """
    Color for a file format.
    Returns a terminal color code based on the format type.
    """
    from kash.config import colors

    if not format:
        return ""

    if format == Format.url:
        return colors.terminal.blue_dark
    if format.is_image:
        return colors.terminal.magenta_darker
    if format.is_audio:
        return colors.terminal.cyan_darker
    if format.is_video:
        return colors.terminal.magenta_dark
    if format.is_code:
        return colors.terminal.yellow_darker
    if format.is_data:
        return colors.terminal.cyan_dark
    # Remaining text formats including markdown, plaintext, etc.
    if format.is_text:
        return colors.terminal.green_darker
    if format.is_doc:
        return colors.terminal.green_dark
    if format.is_binary:
        return colors.terminal.red_dark

    # Anything else not recognized.
    return ""
