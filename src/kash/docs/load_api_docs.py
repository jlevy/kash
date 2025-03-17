from kash.config.logger import get_logger
from kash.docs.load_help_topics import load_help_src
from kash.docs.load_source_code import load_source_code
from kash.utils.common.string_template import StringTemplate

log = get_logger(__name__)


def load_api_docs() -> str:
    template_str = load_help_src("markdown/api_docs_template")
    template_vars = list(load_source_code().__dict__.keys())
    template = StringTemplate(template_str, template_vars)
    return template.format(**load_source_code().__dict__)
