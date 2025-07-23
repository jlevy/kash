from types import SimpleNamespace

from colour import Color
from rich.terminal_theme import TerminalTheme


def hsl_to_hex(hsl_string: str) -> str:
    """
    Convert an HSL/HSLA string to an RGB hex string or RGBA value.
    "hsl(134, 43%, 60%)" -> "#6dbd6d"
    "hsla(220, 14%, 96%, 0.86)" -> "rgba(244, 245, 247, 0.86)"
    """
    is_hsla = hsl_string.startswith("hsla")
    hsl_values = (
        hsl_string.replace("hsla(", "")
        .replace("hsl(", "")
        .replace(")", "")
        .replace("%", "")
        .split(",")
    )

    if is_hsla:
        hue, saturation, lightness, alpha = (float(value.strip()) for value in hsl_values)
    else:
        hue, saturation, lightness = (float(value.strip()) for value in hsl_values)
        alpha = 1.0

    saturation /= 100
    lightness /= 100

    color = Color(hsl=(hue / 360, saturation, lightness))

    if alpha < 1:
        rgb = color.rgb
        return f"rgba({int(rgb[0] * 255)}, {int(rgb[1] * 255)}, {int(rgb[2] * 255)}, {alpha})"
    return color.hex_l


def hex_to_int(hex_string: str) -> tuple[int, int, int]:
    """
    Convert a hex color string to RGB integers.
    Supports both 6-digit and 3-digit hex codes:
    "#6dbd6d" -> (109, 189, 109)
    "#333" -> (51, 51, 51)  # equivalent to #333333
    """
    try:
        hex_string = hex_string.lstrip("#")
        if len(hex_string) == 3:
            hex_string = "".join(c + c for c in hex_string)
        if len(hex_string) != 6:
            raise ValueError(f"Invalid hex color length: {hex_string}")

        r = int(hex_string[0:2], 16)
        g = int(hex_string[2:4], 16)
        b = int(hex_string[4:6], 16)

        return (r, g, b)
    except Exception:
        raise ValueError(f"Could not parse hex color: `{hex_string}`")


# Main colors.
terminal_colors = SimpleNamespace(
    # Based on:
    # https://rootloops.sh?sugar=8&colors=7&sogginess=5&flavor=2&fruit=9&milk=1
    # Some tools only like hex colors so convert them at once.
    # black
    black_darkest=hsl_to_hex("hsl(0, 0%, 7%)"),
    black_darker=hsl_to_hex("hsl(0, 0%, 13%)"),
    black_dark=hsl_to_hex("hsl(0, 0%, 30%)"),
    black_light=hsl_to_hex("hsl(0, 0%, 73%)"),
    black_lighter=hsl_to_hex("hsl(0, 0%, 90%)"),
    # red
    red_darkest=hsl_to_hex("hsl(7, 50%, 35%)"),
    red_darker=hsl_to_hex("hsl(7, 43%, 48%)"),
    red_dark=hsl_to_hex("hsl(7, 73%, 72%)"),
    red_light=hsl_to_hex("hsl(7, 87%, 85%)"),
    red_lighter=hsl_to_hex("hsl(7, 95%, 94%)"),
    # green
    green_darkest=hsl_to_hex("hsl(134, 35%, 34%)"),
    green_darker=hsl_to_hex("hsl(134, 37%, 46%)"),
    green_dark=hsl_to_hex("hsl(134, 43%, 60%)"),
    green_light=hsl_to_hex("hsl(134, 53%, 73%)"),
    green_lighter=hsl_to_hex("hsl(134, 70%, 90%)"),
    # yellow
    yellow_darkest=hsl_to_hex("hsl(44, 47%, 34%)"),
    yellow_darker=hsl_to_hex("hsl(44, 47%, 44%)"),
    yellow_dark=hsl_to_hex("hsl(44, 54%, 55%)"),
    yellow_light=hsl_to_hex("hsl(44, 74%, 76%)"),
    yellow_lighter=hsl_to_hex("hsl(44, 80%, 90%)"),
    # blue
    blue_darkest=hsl_to_hex("hsl(225, 35%, 34%)"),
    blue_darker=hsl_to_hex("hsl(225, 46%, 52%)"),
    blue_dark=hsl_to_hex("hsl(225, 71%, 76%)"),
    blue_light=hsl_to_hex("hsl(225, 86%, 88%)"),
    blue_lighter=hsl_to_hex("hsl(225, 90%, 94%)"),
    # magenta
    magenta_darkest=hsl_to_hex("hsl(305, 35%, 34%)"),
    magenta_darker=hsl_to_hex("hsl(305, 38%, 55%)"),
    magenta_dark=hsl_to_hex("hsl(305, 54%, 71%)"),
    magenta_light=hsl_to_hex("hsl(305, 68%, 85%)"),
    magenta_lighter=hsl_to_hex("hsl(305, 96%, 95%)"),
    # cyan
    cyan_darkest=hsl_to_hex("hsl(188, 60%, 32%)"),
    cyan_darker=hsl_to_hex("hsl(188, 60%, 41%)"),
    cyan_dark=hsl_to_hex("hsl(188, 58%, 57%)"),
    cyan_light=hsl_to_hex("hsl(188, 52%, 76%)"),
    cyan_lighter=hsl_to_hex("hsl(188, 52%, 92%)"),
    # white
    white_darkest=hsl_to_hex("hsl(240, 6%, 60%)"),
    white_darker=hsl_to_hex("hsl(240, 6%, 72%)"),
    white_dark=hsl_to_hex("hsl(240, 6%, 87%)"),
    white_light=hsl_to_hex("hsl(240, 6%, 94%)"),
    white_lighter=hsl_to_hex("hsl(240, 6%, 98%)"),
)


# Only support dark terminal colors for now.
terminal_dark = SimpleNamespace(
    foreground="#fff",
    background="#000",
    border=hsl_to_hex("hsl(188, 8%, 33%)"),
    cursor=hsl_to_hex("hsl(305, 84%, 68%)"),
    input=hsl_to_hex("hsl(305, 92%, 95%)"),
    input_form=hsl_to_hex("hsl(188, 52%, 76%)"),
    **terminal_colors.__dict__,
)
terminal = terminal_dark


# Web light colors.
web_light_translucent = SimpleNamespace(
    primary=hsl_to_hex("hsl(188, 31%, 41%)"),
    primary_light=hsl_to_hex("hsl(188, 40%, 62%)"),
    secondary=hsl_to_hex("hsl(188, 12%, 28%)"),
    tertiary=hsl_to_hex("hsl(188, 7%, 64%)"),
    bg=hsl_to_hex("hsla(44, 6%, 100%, 0.75)"),
    bg_solid=hsl_to_hex("hsl(44, 6%, 100%)"),
    bg_header=hsl_to_hex("hsla(188, 42%, 70%, 0.2)"),
    bg_alt=hsl_to_hex("hsla(39, 24%, 90%, 0.3)"),
    bg_alt_solid=hsl_to_hex("hsl(39, 24%, 97%)"),
    bg_meta_solid=hsl_to_hex("hsl(39, 24%, 94%)"),
    bg_strong_solid=hsl_to_hex("hsl(39, 8%, 90%)"),
    bg_selected=hsl_to_hex("hsla(188, 21%, 94%, 0.9)"),
    text=hsl_to_hex("hsl(188, 39%, 11%)"),
    code=hsl_to_hex("hsl(44, 38%, 23%)"),
    border=hsl_to_hex("hsl(188, 8%, 50%)"),
    border_hairline=hsl_to_hex("hsl(188, 2%, 34%)"),
    border_hint=hsl_to_hex("hsla(188, 8%, 72%, 0.3)"),
    border_accent=hsl_to_hex("hsla(305, 18%, 65%, 0.85)"),
    hover=hsl_to_hex("hsl(188, 12%, 84%)"),
    hover_bg=hsl_to_hex("hsla(188, 18%, 97%, 1)"),
    hint=hsl_to_hex("hsl(188, 11%, 65%)"),
    hint_strong=hsl_to_hex("hsl(188, 11%, 46%)"),
    hint_gentle=hsl_to_hex("hsla(188, 11%, 65%, 0.2)"),
    tooltip_bg=hsl_to_hex("hsla(188, 6%, 37%, 0.7)"),
    popover_bg=hsl_to_hex("hsla(188, 6%, 37%, 0.7)"),
    bright=hsl_to_hex("hsl(134, 43%, 60%)"),
    success=hsl_to_hex("hsl(134, 70%, 37%)"),
    failure=hsl_to_hex("hsl(7, 70%, 37%)"),
    selection="hsla(225, 61%, 82%, 0.80)",
    scrollbar=hsl_to_hex("hsla(189, 12%, 55%, 0.9)"),
    scrollbar_hover=hsl_to_hex("hsla(190, 12%, 38%, 0.9)"),
)


# Web dark colors
web_dark_translucent = SimpleNamespace(
    primary=hsl_to_hex("hsl(188, 40%, 62%)"),
    primary_light=hsl_to_hex("hsl(188, 50%, 72%)"),
    secondary=hsl_to_hex("hsl(188, 12%, 70%)"),
    tertiary=hsl_to_hex("hsl(188, 7%, 45%)"),
    bg=hsl_to_hex("hsla(220, 14%, 7%, 0.95)"),
    bg_solid=hsl_to_hex("hsl(220, 14%, 7%)"),
    bg_header=hsl_to_hex("hsla(188, 42%, 20%, 0.3)"),
    bg_alt=hsl_to_hex("hsla(220, 14%, 12%, 0.5)"),
    bg_alt_solid=hsl_to_hex("hsl(220, 15%, 16%)"),
    bg_meta_solid=hsl_to_hex("hsl(220, 14%, 25%)"),
    bg_strong_solid=hsl_to_hex("hsl(220, 14%, 35%)"),
    bg_selected=hsl_to_hex("hsla(188, 13%, 33%, 0.95)"),
    text=hsl_to_hex("hsl(188, 10%, 90%)"),
    code=hsl_to_hex("hsl(44, 38%, 72%)"),
    border=hsl_to_hex("hsl(188, 8%, 25%)"),
    border_hairline=hsl_to_hex("hsl(188, 2%, 80%)"),
    border_hint=hsl_to_hex("hsla(188, 8%, 35%, 0.3)"),
    border_accent=hsl_to_hex("hsla(305, 30%, 55%, 0.85)"),
    hover=hsl_to_hex("hsl(188, 12%, 35%)"),
    hover_bg=hsl_to_hex("hsla(188, 12%, 40%, 0.95)"),
    hint=hsl_to_hex("hsl(188, 11%, 55%)"),
    hint_strong=hsl_to_hex("hsl(188, 11%, 72%)"),
    hint_gentle=hsl_to_hex("hsla(188, 11%, 55%, 0.2)"),
    tooltip_bg=hsl_to_hex("hsla(188, 6%, 20%, 0.9)"),
    popover_bg=hsl_to_hex("hsla(188, 6%, 20%, 0.9)"),
    bright=hsl_to_hex("hsl(134, 52%, 65%)"),
    success=hsl_to_hex("hsl(134, 72%, 73%)"),
    failure=hsl_to_hex("hsl(7, 46%, 53%)"),
    selection=hsl_to_hex("hsla(225, 61%, 40%, 0.40)"),
    scrollbar=hsl_to_hex("hsla(189, 12%, 35%, 0.9)"),
    scrollbar_hover=hsl_to_hex("hsla(190, 12%, 50%, 0.9)"),
)


rich_terminal_dark = TerminalTheme(
    hex_to_int(terminal_dark.background),
    hex_to_int(terminal_dark.foreground),
    # normal colors [black, red, green, yellow, blue, magenta, cyan, white]
    [
        hex_to_int(terminal_dark.black_dark),
        hex_to_int(terminal_dark.red_dark),
        hex_to_int(terminal_dark.green_dark),
        hex_to_int(terminal_dark.yellow_dark),
        hex_to_int(terminal_dark.blue_dark),
        hex_to_int(terminal_dark.magenta_dark),
        hex_to_int(terminal_dark.cyan_dark),
        hex_to_int(terminal_dark.white_dark),
    ],
    # bright colors [black, red, green, yellow, blue, magenta, cyan, white]
    [
        hex_to_int(terminal_dark.black_lighter),
        hex_to_int(terminal_dark.red_lighter),
        hex_to_int(terminal_dark.green_lighter),
        hex_to_int(terminal_dark.yellow_lighter),
        hex_to_int(terminal_dark.blue_lighter),
        hex_to_int(terminal_dark.magenta_lighter),
        hex_to_int(terminal_dark.cyan_lighter),
        hex_to_int(terminal_dark.white_lighter),
    ],
)

rich_terminal_light = TerminalTheme(
    hex_to_int(terminal_dark.background),
    hex_to_int(terminal_dark.foreground),
    # normal colors [black, red, green, yellow, blue, magenta, cyan, white]
    [
        hex_to_int(terminal_dark.black_dark),
        hex_to_int(terminal_dark.red_dark),
        hex_to_int(terminal_dark.green_dark),
        hex_to_int(terminal_dark.yellow_dark),
        hex_to_int(terminal_dark.blue_dark),
        hex_to_int(terminal_dark.magenta_dark),
        hex_to_int(terminal_dark.cyan_dark),
        hex_to_int(terminal_dark.white_dark),
    ],
    # bright colors [black, red, green, yellow, blue, magenta, cyan, white]
    [
        hex_to_int(terminal_dark.black_darker),
        hex_to_int(terminal_dark.red_darker),
        hex_to_int(terminal_dark.green_darker),
        hex_to_int(terminal_dark.yellow_darker),
        hex_to_int(terminal_dark.blue_darker),
        hex_to_int(terminal_dark.magenta_darker),
        hex_to_int(terminal_dark.cyan_darker),
        hex_to_int(terminal_dark.white_darker),
    ],
)

# We default to light colors for Rich content in HTML.
rich_terminal = rich_terminal_light

# Logical colors
logical = SimpleNamespace(
    concept_dark=terminal.green_dark,
    concept_light=terminal.green_light,
    concept_lighter=terminal.green_lighter,
    doc_dark=terminal.blue_dark,
    doc_light=terminal.blue_light,
    doc_lighter=terminal.blue_lighter,
    resource_dark=terminal.cyan_dark,
    resource_light=terminal.cyan_light,
    resource_lighter=terminal.cyan_lighter,
    link_dark=terminal.yellow_dark,
    link_light=terminal.yellow_light,
    link_lighter=terminal.yellow_lighter,
    other=terminal.white_dark,
    other_light=terminal.white_light,
    other_lighter=terminal.white_lighter,
)


def consolidate_color_vars(
    overrides: dict[str, str] | None = None, web_colors: SimpleNamespace | None = None
) -> dict[str, str]:
    """
    Consolidate all color variables into a single dictionary with appropriate prefixes.
    Terminal variables have no prefix, while web and logical variables have "color-" prefix.
    """
    if overrides is None:
        overrides = {}
    if web_colors is None:
        web_colors = web_light_translucent

    return {
        # Terminal variables (no prefix)
        **terminal.__dict__,
        # Web and logical variables with "color-" prefix
        **{f"color-{k}": v for k, v in web_colors.__dict__.items()},
        **{f"color-{k}": v for k, v in logical.__dict__.items()},
        # Overrides take precedence (assume they already have correct prefixes)
        **overrides,
    }


def normalize_var_names(variables: dict[str, str]) -> dict[str, str]:
    """
    Normalize variable names from Python style to CSS style.
    Example: color_bg -> color-bg
    """
    return {k.replace("_", "-"): v for k, v in variables.items()}


def generate_css_vars(overrides: dict[str, str] | None = None) -> str:
    """
    Generate CSS variables for terminal and both light and dark themes.
    """
    if overrides is None:
        overrides = {}

    # Get base variables (terminal colors stay the same)
    base_vars = normalize_var_names({k: v for k, v in terminal.__dict__.items()})

    # Get light theme color variables
    light_color_vars = normalize_var_names(
        {f"color-{k}": v for k, v in web_light_translucent.__dict__.items()}
    )
    light_color_vars.update(
        normalize_var_names({f"color-{k}": v for k, v in logical.__dict__.items()})
    )

    # Get dark theme color variables
    dark_color_vars = normalize_var_names(
        {f"color-{k}": v for k, v in web_dark_translucent.__dict__.items()}
    )
    dark_color_vars.update(
        normalize_var_names({f"color-{k}": v for k, v in logical.__dict__.items()})
    )

    # Apply overrides
    if overrides:
        normalized_overrides = normalize_var_names(overrides)
        light_color_vars.update(normalized_overrides)
        dark_color_vars.update(normalized_overrides)

    # Generate CSS
    css_parts = []

    # Root with all variables (defaults to light)
    css_parts.append(":root {")
    css_parts.extend(f"  --{k}: {v};" for k, v in base_vars.items())
    css_parts.extend(f"  --{k}: {v};" for k, v in light_color_vars.items())
    css_parts.append("}\n")

    # Light theme (only color- variables)
    css_parts.append('[data-theme="light"] {')
    css_parts.extend(f"  --{k}: {v};" for k, v in light_color_vars.items())
    css_parts.append("}\n")

    # Dark theme (only color- variables)
    css_parts.append('[data-theme="dark"] {')
    css_parts.extend(f"  --{k}: {v};" for k, v in dark_color_vars.items())
    css_parts.append("}\n")

    # Print media
    css_parts.append("@media print {")
    css_parts.append('  :root, [data-theme="dark"] {')
    css_parts.extend(f"    --{k}: {v} !important;" for k, v in light_color_vars.items())
    css_parts.append("  }")
    css_parts.append("}")

    return "\n".join(css_parts)


if __name__ == "__main__":
    print(generate_css_vars())
