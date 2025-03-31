from chopdiff.divs import CHUNK, ORIGINAL, RESULT, TextNode
from pydantic.dataclasses import dataclass
from typing_extensions import override

from kash.config.logger import get_logger
from kash.exec.llm_transforms import llm_transform_str
from kash.exec.preconditions import has_div_chunks
from kash.model.actions_model import PerItemAction
from kash.model.items_model import Item
from kash.model.preconditions_model import Precondition
from kash.utils.common.task_stack import task_stack
from kash.utils.errors import InvalidInput
from kash.utils.file_utils.file_formats_model import Format

log = get_logger(__name__)


@dataclass
class ChunkedLLMAction(PerItemAction):
    """
    Base class for LLM actions that operate on chunks that are already marked with divs.
    """

    precondition: Precondition = has_div_chunks

    chunk_class: str = CHUNK

    @override
    def __post_init__(self):
        super().__post_init__()

    @override
    def run_item(self, item: Item) -> Item:
        from chopdiff.divs.parse_divs import parse_divs_by_class

        if not item.body:
            raise InvalidInput(f"LLM actions expect a body: {self.name} on {item}")

        output = []
        chunks = parse_divs_by_class(item.body, self.chunk_class)

        with task_stack().context(self.name, len(chunks), "chunk") as ts:
            for chunk in chunks:
                output.append(self.process_chunk(chunk))
                ts.next()

        result_item = item.derived_copy(
            type=item.type, body="\n\n".join(output), format=Format.md_html
        )

        return result_item

    def process_chunk(self, chunk: "TextNode") -> str:
        """
        Override to customize chunk handling.
        """
        from chopdiff.divs.div_elements import div, div_get_original, div_insert_wrapped

        transform_input = div_get_original(chunk, child_name=ORIGINAL)
        llm_response = llm_transform_str(self.llm_options, transform_input)
        new_div = div(RESULT, llm_response)

        return div_insert_wrapped(chunk, [new_div], container_class=CHUNK, original_class=ORIGINAL)
