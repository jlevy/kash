from kash.exec import kash_action, llm_transform_item
from kash.llm_utils import LLM, LLMName, Message, MessageTemplate
from kash.model import Item, LLMOptions, common_params

llm_options = LLMOptions(
    system_message=Message(
        """
        You are a careful and precise editor.
        You give exactly the results requested without additional commentary.
        """
    ),
    body_template=MessageTemplate(
        """
        Summarize the following text as a list of concise bullet points:

        - Each point should be one sentence long.

        - Format your response as a list of bullet points in Markdown format.

        - Do NOT use nested bullet points. Give a single list, not a list of lists.
        
        - Include all key numbers or facts, without omitting any claims or important details.
        
        - Use simple and precise language.

        - Simply state the facts or claims without referencing the text or the author. For example, if the
          text is about cheese being nutritious, you can say "Cheese is nutritious." But do NOT
          say "The author says cheese is nutritious" or "According to the text, cheese is nutritious."

        - It is very important you do not add any details that are not directly stated in the original text.
          Do not change any numbers or alter its meaning in any way.

        - Do NOT give any additional response at the beginning, such as "Here are the concise bullet points".
          Simply give the summary.

        - If the input is very short or so unclear you can't summarize it, simply output "(No results)".

        - If the input is in a language other than English, output the summary in the same language.

        Input text:

        {body}

        Bullet points:
        """
    ),
)


@kash_action(llm_options=llm_options, params=common_params("model"), mcp_tool=True)
def summarize_as_bullets(item: Item, model: LLMName = LLM.default_standard) -> Item:
    """
    Summarize text as bullet points.
    """
    return llm_transform_item(item, model=model)
