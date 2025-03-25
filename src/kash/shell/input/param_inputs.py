from kash.model.params_model import Param
from kash.shell.input.input_prompts import input_choice, input_simple_string


def input_param_name(prompt_text: str, settable_params: dict[str, Param]) -> Param | None:
    param_name = input_choice(
        prompt_text,
        choices=list(settable_params.keys()),
        mandatory=True,
    )
    return settable_params[param_name] if param_name else None


def input_param_value(prompt_text: str, param: Param) -> str | None:
    if param.valid_values:
        param_value = input_choice(prompt_text, choices=param.valid_values, mandatory=False)
    else:
        param_value = input_simple_string(prompt_text, default=param.default_value_str or "")
    return param_value
