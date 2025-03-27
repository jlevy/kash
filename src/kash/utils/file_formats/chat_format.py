"""
YAML chat format is a simple file format for chat messages or commands that's just
YAML blocks separated by the usual YAML `---` separator, with a few conventions.

This format can represent data like OpenAI JSON
[chat messages](https://platform.openai.com/docs/guides/text-generation#messages-and-roles)
as well as any other kind of command or message.

It has a few benefits over raw JSON:

- It's more human-editable than JSON and more readable, especially for
  git diffs.

- Multiline strings are easy to read and edit if `|`-style literals
  are used for the content:
  https://yaml.org/spec/1.2.2/#812-literal-style

- Unlike with a JSON object or array, chat messages can be appended to a file
  without rewriting any content.

Rules:

- The content is valid YAML blocks with standard `---` separators.

- An initial `---` is required (to make file type detection easier).

- Any YAML is valid in a block, as long as it contains `role` and `content`
  string fields.

- The `content` field can be a string or a dictionary with additional fields
  (useful for structured output chat responses).

- It's recommended but not required that `role` be one of the
  following: "user", "assistant", "system", "developer", "command",
  "output", or "template".

Note this is the same as any YAML frontmatter, but the `role`
field indicates the file is in chat format.

Chat example:

```
---
role: system
content: |
  You are a helpful assistant.
---
role: user
content: |
  Hello, how are you?
---
role: assistant
content: |
  I'm fine, thank you!
---
role: user
content: |
  Give me a hello world.
---
role: assistant
content:
  code: |
    def hello_world():
        print("Hello, world!")
  explanation: A simple function that prints a greeting.
```

Command example:
```
---
role: command
content: |
  transcribe_video
---
role: output
content: |
  The video has been transcribed.
output_file: /path/to/video.txt
```

Template example:
```
---
role: template
template_vars: ["name", "body"]
content: |
  Hello, {name}! Here is your message:
  {body}
---
```

"""

from __future__ import annotations

import json
from dataclasses import field
from enum import Enum
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Any

from frontmatter_format import from_yaml_string, new_yaml, to_yaml_string
from prettyfmt import abbrev_obj, custom_key_sort, fmt_size_human
from pydantic.dataclasses import dataclass


class ChatRole(str, Enum):
    """
    The role of a message in a chat. Represents the "role" in LLM APIs but note we slightly
    abuse this term to also represent other types of messages, such as commands issued
    by the user, output from the system, or a template that may contain template variables.
    """

    user = "user"
    assistant = "assistant"
    system = "system"
    developer = "developer"
    command = "command"
    output = "output"
    template = "template"


_custom_key_sort = custom_key_sort(["role", "content"])

ChatContent = str | dict[str, Any]


@dataclass
class ChatMessage:
    role: ChatRole
    content: ChatContent
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, message_dict: dict[str, Any]) -> ChatMessage:
        try:
            message_copy = message_dict.copy()
            role_str = message_copy.pop("role")
            if isinstance(role_str, str):
                role = ChatRole(role_str)
            else:
                role = role_str
            content = message_copy.pop("content")
            metadata = message_copy
            return cls(role=role, content=content, metadata=metadata)
        except LookupError as e:
            raise ValueError("Could not parse chat message") from e

    def as_dict(self) -> dict[str, Any]:
        data = {
            "role": (self.role.value if isinstance(self.role, Enum) else self.role),
            "content": self.content,
        }
        data.update(self.metadata)
        return data

    def as_chat_completion(self) -> dict[str, str]:
        """
        Convert to a format that can be used as a standard chat completion, with
        the content field holding JSON-serialized data if it is structured.
        """
        return {
            "role": self.role.value,
            "content": json.dumps(self.content) if isinstance(self.content, dict) else self.content,
        }

    @classmethod
    def from_yaml(cls, yaml_string: str) -> ChatMessage:
        return cls.from_dict(from_yaml_string(yaml_string))

    def to_yaml(self) -> str:
        return to_yaml_string(self.as_dict(), key_sort=_custom_key_sort)

    def to_json(self) -> str:
        return json.dumps(self.as_dict())

    def as_str(self) -> str:
        return self.to_yaml()

    def as_str_brief(self) -> str:
        return abbrev_obj(self)

    def __str__(self) -> str:
        return self.as_str_brief()


@dataclass
class ChatHistory:
    messages: list[ChatMessage] = field(default_factory=list)

    def append(self, message: ChatMessage) -> None:
        self.messages.append(message)

    def extend(self, messages: list[ChatMessage]) -> None:
        self.messages.extend(messages)

    @classmethod
    def from_dicts(cls, message_dicts: list[dict[str, Any]]) -> ChatHistory:
        messages = [ChatMessage.from_dict(message_dict) for message_dict in message_dicts]
        return cls(messages=messages)

    @classmethod
    def from_yaml(cls, yaml_string: str) -> ChatHistory:
        yaml = new_yaml()
        message_dicts = yaml.load_all(yaml_string)
        messages = [
            ChatMessage.from_dict(message_dict) for message_dict in message_dicts if message_dict
        ]
        return cls(messages=messages)

    def as_chat_completion(self) -> list[dict[str, str]]:
        return [message.as_chat_completion() for message in self.messages]

    def to_yaml(self) -> str:
        yaml = new_yaml(key_sort=_custom_key_sort, typ="rt")
        stream = StringIO()
        # Include the extra `---` at the front for consistency and to make this file identifiable.
        stream.write("---\n")
        yaml.dump_all([message.as_dict() for message in self.messages], stream)
        return stream.getvalue()

    def to_json(self) -> str:
        return json.dumps([message.as_dict() for message in self.messages])

    def size_summary(self) -> str:
        role_counts = {}
        for msg in self.messages:
            role_counts[msg.role.value] = role_counts.get(msg.role.value, 0) + 1

        counts = [f"{count} {role}" for role, count in role_counts.items()]
        return f"{len(self.messages)} messages ({', '.join(counts)}, {fmt_size_human(len(self.to_json()))} bytes total)"

    def as_str(self) -> str:
        return self.to_yaml()

    def as_str_brief(self) -> str:
        return abbrev_obj(self)

    def __str__(self) -> str:
        return self.as_str_brief()


def append_chat_message(path: Path, message: ChatMessage, make_parents: bool = True) -> None:
    """
    Append a chat message to a YAML file. Creates the file if it doesn't exist.
    """
    if make_parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write("---\n")
        file.write(message.to_yaml())


def tail_chat_history(path: Path, max_records: int) -> ChatHistory:
    """
    Show last few results from a chat history file.
    """
    with path.open("r", encoding="utf-8") as file:
        contents = file.read()

    chat_history = ChatHistory.from_yaml(contents)
    if max_records > 0:
        chat_history.messages = chat_history.messages[-max_records:]

    return chat_history


## Tests


def test_chat_history_serialization():
    from textwrap import dedent

    yaml_input = dedent(
        """
        role: system
        content: |
          You are a helpful assistant.
        ---
        role: user
        content: |
          Hello, how are you?
        ---
        role: assistant
        content: |
          I'm fine, thank you!
        mood: happy
        ---
        role: command
        content: |
          transcribe_video
        ---
        role: output
        content: |
          The video has been transcribed.
        output_file: /path/to/video.txt
        ---
        role: template
        template_vars: ["name", "body"]
        content: |
          Hello, {name}! Here is your message:
          {body}
        """
    ).lstrip()

    chat_history = ChatHistory.from_yaml(yaml_input)
    yaml_output = chat_history.to_yaml()

    print("\nSerialized YAML output:")
    print(yaml_output)

    print("\nFirst message:")
    print(repr(chat_history.messages[0]))

    assert chat_history.messages[0] == ChatMessage(
        role=ChatRole.system, content="You are a helpful assistant.\n", metadata={}
    )

    for message in chat_history.messages:
        assert isinstance(message.role, ChatRole)

    # Tolerate no initial `---` or an extra final `---`.
    assert chat_history == ChatHistory.from_yaml(yaml_output)
    assert chat_history == ChatHistory.from_yaml("---\n" + yaml_input + "\n---\n")

    test_dict = {
        "role": "user",
        "content": "Testing role as string.",
    }
    message_from_string = ChatMessage.from_dict(test_dict)
    assert message_from_string.role == ChatRole.user

    test_dict_enum = {
        "role": ChatRole.assistant,
        "content": "Testing role as Enum.",
    }
    message_from_enum = ChatMessage.from_dict(test_dict_enum)
    assert message_from_enum.role == ChatRole.assistant

    # Confirm we use multi-line literals.
    test_long_message = ChatMessage(
        role=ChatRole.system,
        content="\n".join(["line " + str(i) for i in range(10)]),
    )
    print("test_long_message", test_long_message.to_yaml())
    yaml = test_long_message.to_yaml()
    assert len(yaml.splitlines()) > 10
    assert "content: |" in yaml


def test_from_dict():
    """Test basic dictionary parsing functionality."""
    message_dict = {
        "role": "assistant",
        "content": "Hello world",
        "temperature": 0.7,
    }

    message = ChatMessage.from_dict(message_dict)
    assert message.role == ChatRole.assistant
    assert message.content == "Hello world"
    assert message.metadata == {"temperature": 0.7}
    assert message.as_dict() == message_dict


def test_structured_content():
    structured_yaml = dedent(
        """
        ---
        role: assistant
        content:
            thought: I need to parse this JSON
            steps:
                - Read the input
                - Parse using json.loads
            code: |
                import json
                data = json.loads(input_str)
        ---
        role: assistant
        content:
            result: success
            parsed_items: 42
            details:
                errors: []
                warnings: null
        """
    ).lstrip()

    chat_history = ChatHistory.from_yaml(structured_yaml)

    first_msg = chat_history.messages[0]
    assert isinstance(first_msg.content, dict)
    assert first_msg.content["thought"] == "I need to parse this JSON"
    assert len(first_msg.content["steps"]) == 2
    assert "code" in first_msg.content

    second_msg = chat_history.messages[1]
    assert isinstance(second_msg.content, dict)
    assert second_msg.content["result"] == "success"
    assert second_msg.content["parsed_items"] == 42
    assert isinstance(second_msg.content["details"], dict)

    yaml_output = chat_history.to_yaml()
    reloaded = ChatHistory.from_yaml(yaml_output)
    assert reloaded.messages[0].content == first_msg.content
    assert reloaded.messages[1].content == {
        "result": "success",
        "parsed_items": 42,
        "details": {"errors": []},  # null field is dropped.
    }
