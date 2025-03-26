from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import asdict, field, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from frontmatter_format import from_yaml_string, new_yaml
from prettyfmt import abbrev_obj, abbrev_on_words, abbrev_phrase_in_middle, sanitize_title
from pydantic.dataclasses import dataclass
from slugify import slugify
from strif import abbrev_str, format_iso_timestamp

from kash.concepts.concept_formats import canonicalize_concept
from kash.config.logger import get_logger
from kash.errors import FileFormatError
from kash.model.media_model import MediaMetadata
from kash.model.operations_model import OperationSummary, Source
from kash.model.paths_model import StorePath, fmt_store_path
from kash.text_handling.markdown_util import markdown_to_html
from kash.utils.common.format_utils import fmt_loc, html_to_plaintext, plaintext_to_html
from kash.utils.common.url import Locator, Url
from kash.utils.file_formats.chat_format import ChatHistory
from kash.utils.file_utils.file_formats_model import FileExt, Format

if TYPE_CHECKING:
    from kash.model.actions_model import ExecContext

log = get_logger(__name__)

T = TypeVar("T")


class ItemType(Enum):
    """
    Kinds of items. The `ItemType` represents the way it is used by the user,
    and not necessarily the format of the data. For example, an HTML file could
    be a resource (something imported from the web) or a doc (something written
    or being processed by the user) or an export (something generated by for
    a specific use).
    """

    doc = "doc"
    concept = "concept"
    resource = "resource"
    asset = "asset"
    config = "config"
    export = "export"
    chat = "chat"
    extension = "extension"
    script = "script"
    log = "log"

    @property
    def expects_body(self) -> bool:
        """
        Resources don't have a body. On concepts it's optional.
        """
        return self.value not in [ItemType.resource.value, ItemType.concept.value]

    @staticmethod
    def for_format(format: Format) -> ItemType:
        """
        Default item type for this format, mainly for default guess when importing.
        """
        from kash.model.items_model import ItemType

        format_to_item_type = {
            Format.url: ItemType.resource,
            Format.plaintext: ItemType.doc,
            Format.markdown: ItemType.doc,
            Format.md_html: ItemType.doc,
            Format.html: ItemType.doc,
            Format.yaml: ItemType.doc,
            Format.diff: ItemType.doc,
            Format.python: ItemType.extension,
            Format.kash_script: ItemType.extension,
            Format.json: ItemType.doc,
            Format.csv: ItemType.doc,
            Format.log: ItemType.log,
            Format.pdf: ItemType.resource,
            Format.jpeg: ItemType.asset,
            Format.png: ItemType.asset,
            Format.docx: ItemType.resource,
            Format.mp3: ItemType.resource,
            Format.m4a: ItemType.resource,
            Format.mp4: ItemType.resource,
        }
        return format_to_item_type.get(format, ItemType.resource)


class State(Enum):
    """
    Review state of an item. Draft is default. Transient is used for items that may be
    safely auto-archived.
    """

    draft = "draft"
    reviewed = "reviewed"
    transient = "transient"


class IdType(Enum):
    """
    Types of identity checks.
    """

    url = "url"
    concept = "concept"
    source = "source"


@dataclass(frozen=True)
class ItemId:
    """
    Represents the identity of an item. The id is used as a shortcut to determine
    if an object already exists.

    The identity of an entity like a URL or a concept is just itself.

    The identity of some items is their source, i.e. the process by which
    they were created, e.g. a transcription of a URL.
    We can decide if an item already exists if we have an output of the same
    action on the exact same inputs, and the action is cacheable (i.e. we consider
    it deterministic).

    If the item is something like a chat with the user, it has no item id because
    every chat is unique (a chat action would be non-cacheable).
    """

    type: ItemType
    id_type: IdType
    value: str

    def id_str(self):
        return f"id:{self.id_type.value}:{self.value.replace(' ', '_')}"

    def __str__(self):
        return self.id_str()

    @classmethod
    def for_item(cls, item: Item) -> ItemId | None:
        from kash.web_content.canon_url import canonicalize_url

        item_id = None
        if item.type == ItemType.resource and item.format == Format.url and item.url:
            item_id = ItemId(item.type, IdType.url, canonicalize_url(item.url))
        elif item.type == ItemType.concept and item.title:
            item_id = ItemId(item.type, IdType.concept, canonicalize_concept(item.title))
        elif item.source and item.source.cacheable:
            # We know the source of this and if the action was cacheable, we can create
            # an identity based on the source.
            item_id = ItemId(item.type, IdType.source, item.source.as_str())
        else:
            # If we got here, the item has no identity.
            item_id = None

        return item_id


@dataclass
class ItemRelations:
    """
    Relations of a given item to other items.
    """

    derived_from: list[Locator] | None = None
    diff_of: list[Locator] | None = None
    cites: list[Locator] | None = None

    # TODO: Other relations.
    # named_entities: Optional[List[Locator]] = None
    # related_concepts: Optional[List[Locator]] = None


UNTITLED = "Untitled"

SLUG_MAX_LEN = 64


@dataclass
class Item:
    """
    An Item is any piece of information we may wish to save or perform operations on, such as
    a text document, PDF or other resource, URL, etc.
    """

    type: ItemType
    state: State = State.draft
    title: str | None = None
    url: Url | None = None
    description: str | None = None
    format: Format | None = None
    file_ext: FileExt | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    modified_at: datetime | None = None

    # TODO: Consider adding aliases and tags. See also Obsidian frontmatter format:
    # https://help.obsidian.md/Editing+and+formatting/Properties#Default%20properties

    # Content of the item.
    # Text items are in body. Large or binary items may be stored externally.
    body: str | None = None
    external_path: str | None = None
    original_filename: str | None = None

    # Path to the item in the store, if it has been saved.
    # TODO: Migrate this to StorePath.
    store_path: str | None = None

    # Optionally, relations to other items, including any time this item is derived from.
    relations: ItemRelations = field(default_factory=ItemRelations)

    # The operation that created this item.
    source: Source | None = None

    # Optionally, a history of operations.
    history: list[OperationSummary] | None = None

    # Optionally, a URL to a thumbnail image for this item.
    thumbnail_url: Url | None = None

    # Optional additional metadata.
    extra: dict | None = None

    # Optional execution context. Useful for letting functions that take only an Item
    # arg get access to context.
    context: ExecContext | None = field(default=None, metadata={"exclude": True})

    # These fields we don't want in YAML frontmatter.
    # We don't include store_path as it's redundant with the filename.
    NON_METADATA_FIELDS = ["file_ext", "body", "external_path", "store_path", "context"]

    def __post_init__(self):
        assert isinstance(self.type, ItemType)
        assert self.format is None or isinstance(self.format, Format)
        assert self.file_ext is None or isinstance(self.file_ext, FileExt)

        if not isinstance(self.relations, ItemRelations):
            self.relations = ItemRelations(**self.relations)

    @classmethod
    def from_dict(cls, item_dict: dict[str, Any], **kwargs) -> Item:
        """
        Deserialize fields from a dict that may include string and dict values.
        """
        item_dict = {**item_dict, **kwargs}

        info_prefix = (
            f"{fmt_store_path(item_dict['store_path'])}: " if "store_path" in item_dict else ""
        )

        # Metadata formats might change over time so it's important to gracefully handle issues.
        def set_field(key: str, default: Any, cls_: type[T]) -> T:
            try:
                if key in item_dict:
                    return cls_(item_dict[key])  # pyright: ignore
                else:
                    return default
            except (KeyError, ValueError) as e:
                log.warning(
                    "Error reading %sfield `%s` so using default %r: %s",
                    info_prefix,
                    key,
                    default,
                    e,
                )
                return default

        # These are the enum and dataclass fields.
        type_ = set_field("type", ItemType.doc, ItemType)
        state = set_field("state", State.draft, State)
        format = set_field("format", None, Format)
        file_ext = set_field("file_ext", None, FileExt)
        source = set_field("source", None, Source.from_dict)  # pyright: ignore

        body = item_dict.get("body")
        history = [OperationSummary(**op) for op in item_dict.get("history", [])]
        relations = (
            ItemRelations(**item_dict["relations"]) if "relations" in item_dict else ItemRelations()
        )
        store_path = item_dict.get("store_path")

        # Other fields are basic strings or dicts.
        excluded_fields = [
            "type",
            "state",
            "format",
            "file_ext",
            "body",
            "source",
            "history",
            "relations",
            "store_path",
        ]
        all_fields = [f.name for f in cls.__dataclass_fields__.values()]
        allowed_fields = [f for f in all_fields if f not in excluded_fields]
        other_metadata = {key: value for key, value in item_dict.items() if key in allowed_fields}
        unexpected_metadata = {
            key: value for key, value in item_dict.items() if key not in all_fields
        }
        if unexpected_metadata:
            log.info("Skipping unexpected metadata on item: %s%s", info_prefix, unexpected_metadata)

        result = cls(
            type=type_,
            state=state,
            format=format,
            file_ext=file_ext,
            body=body,
            relations=relations,
            source=source,
            history=history,
            **other_metadata,
            store_path=store_path,
        )
        return result

    @classmethod
    def from_external_path(
        cls, path: Path | str, item_type: ItemType | None = None, title: str | None = None
    ) -> Item:
        """
        Create a resource Item for a file with a format inferred from the file extension
        or the content. Only sets basic metadata. Does not read the content. Will set
        `format` and `file_ext` if possible but will leave them as None if unrecognized.
        """
        from kash.file_storage.store_filenames import parse_item_filename
        from kash.utils.file_utils.file_formats_model import detect_file_format

        # Will raise error for unrecognized file ext.
        _name, filename_item_type, format, file_ext = parse_item_filename(path)
        if not format:
            format = detect_file_format(path)
        if not item_type and filename_item_type:
            item_type = filename_item_type
        if not item_type:
            # Default to doc for general text files and resource for everything else.
            item_type = (
                ItemType.doc if format and format.supports_frontmatter else ItemType.resource
            )
        item = cls(
            type=item_type,
            title=title,
            file_ext=file_ext,
            format=format,
            external_path=str(path),
        )

        # Update modified time from the file system.
        item.set_modified(Path(path).stat().st_mtime)

        return item

    @classmethod
    def from_media_metadata(cls, media_metadata: MediaMetadata) -> Item:
        """
        Create an Item instance from MediaMetadata.
        """
        created_at = (
            datetime.combine(media_metadata.upload_date, datetime.min.time())
            if media_metadata.upload_date
            else datetime.now()
        )
        return cls(
            type=ItemType.resource,
            format=Format.url,
            title=media_metadata.title,
            url=media_metadata.url,
            description=media_metadata.description,
            thumbnail_url=media_metadata.thumbnail_url,
            created_at=created_at,
            extra={
                "media_id": media_metadata.media_id,
                "media_service": media_metadata.media_service,
                "upload_date": media_metadata.upload_date,
                "channel_url": media_metadata.channel_url,
                "view_count": media_metadata.view_count,
                "duration": media_metadata.duration,
                "heatmap": media_metadata.heatmap,
            },
        )

    def validate(self):
        """
        Sanity check the item to ensure it's consistent and complete enough to be saved.
        """
        if not self.format:
            raise ValueError(f"Item has no format: {self}")
        if self.type.expects_body and self.format.has_body and not self.body:
            raise ValueError(f"Item type `{self.type.value}` is text but has no body: {self}")

    @property
    def is_binary(self) -> bool:
        return bool(self.format and self.format.is_binary)

    def set_created(self, timestamp: float):
        self.created_at = datetime.fromtimestamp(timestamp, tz=UTC)

    def set_modified(self, timestamp: float):
        self.modified_at = datetime.fromtimestamp(timestamp, tz=UTC)

    def external_id(self) -> str:
        """
        Semi-permanent external id for the document (for indexing etc.).
        Currently just the store path.
        """
        if not self.store_path:
            raise ValueError("Cannot get doc id for an item that has not been saved")
        return str(self.store_path)

    def metadata(self, datetime_as_str: bool = False) -> dict[str, Any]:
        """
        Metadata is all relevant non-None fields in easy-to-serialize form.
        Optional fields are omitted unless they are set.
        """

        item_dict = self.__dict__.copy()

        # Special case for prettier serialization of input path/hash.
        if self.source:
            item_dict["source"] = self.source.as_dict()

        def serialize(v: Any) -> Any:
            if isinstance(v, list):
                return [serialize(item) for item in v]
            elif isinstance(v, dict):
                return {k: serialize(v) for k, v in v.items()}
            elif isinstance(v, Enum):
                return v.value
            elif hasattr(v, "as_dict"):  # Handle Operation or any object with as_dict method.
                return v.as_dict()
            elif is_dataclass(v) and not isinstance(v, type):
                # Handle Python and Pydantic dataclasses.
                return asdict(v)
            else:
                return v

        # Convert enums and dataclasses to serializable forms.
        log.debug("Item metadata before serialization: %s", item_dict)
        item_dict = {
            k: serialize(v)
            for k, v in item_dict.items()
            if v is not None and k not in self.NON_METADATA_FIELDS
        }
        log.debug("Item metadata after serialization: %s", abbrev_obj(item_dict))

        # Sometimes it's also better to serialize datetimes as strings.
        if datetime_as_str:
            for f, v in item_dict.items():
                if isinstance(v, datetime):
                    item_dict[f] = format_iso_timestamp(v)

        return item_dict

    def display_title(self) -> str:
        """
        A display title for this item. Same as abbrev_title() but will fall back
        to the filename if it is available.
        """
        display_title = self.title
        if not display_title and self.store_path:
            display_title = Path(self.store_path).name
        if not display_title:
            display_title = self.abbrev_title()
        return display_title

    def abbrev_title(self, max_len: int = 100, add_ops_suffix: bool = True) -> str:
        """
        Get or infer a title for this item, falling back to the filename, URL,
        description, or finally body text.
        Optionally, include the last operation as a parenthetical at the end of the title.
        """
        # Special case for URLs with no title..
        if not self.title and self.url:
            return abbrev_str(self.url, max_len)

        # Special case for filenames with no title.
        path_stem = (
            (self.store_path and Path(self.store_path).stem)
            or (self.external_path and Path(self.external_path).stem)
            or (self.original_filename and Path(self.original_filename).stem)
        )
        if not self.title and path_stem:
            return abbrev_str(path_stem, max_len)

        # Otherwise, use the title, description, or body text.
        title_raw_text = (
            self.title
            or self.description
            or (not self.is_binary and self.abbrev_body(max_len))
            or UNTITLED
        )

        suffix = ""
        if add_ops_suffix and self.type not in [ItemType.concept, ItemType.resource]:
            # For notes, exports, etc but not for concepts, add a parenthical note
            # indicating the last operation, if there was one. This makes filename slugs
            # more readable.
            last_op = self.history and self.history[-1].action_name
            if last_op:
                step_num = len(self.history) + 1 if self.history else 1
                suffix = f" (step{step_num:02d}, {last_op})"

        shorter_len = min(max_len, max(max_len - len(suffix), 20))
        clean_text = sanitize_title(
            abbrev_phrase_in_middle(html_to_plaintext(title_raw_text), shorter_len)
        )

        final_text = clean_text
        if len(suffix) + len(clean_text) <= max_len:
            final_text += suffix

        return final_text

    def abbrev_body(self, max_len: int) -> str:
        """
        Get a cut off version of the body text. Must not be a binary Item.
        Abbreviates YAML bodies like {"role": "user", "content": "Hello"} to "user Hello".
        """
        body_text = self.body_text()[:max_len]

        # Just for aesthetics especially for titles of chat files.
        if self.type in [ItemType.chat, ItemType.config] or self.format == Format.yaml:
            try:
                yaml_obj = list(new_yaml().load_all(self.body_text()))
                if len(yaml_obj) > 0:
                    body_text = " ".join(str(v) for v in yaml_obj[0].values())
            except Exception as e:
                log.info("Error parsing YAML body: %s", e)

        return body_text[:max_len]

    def slug_name(self, max_len: int = SLUG_MAX_LEN) -> str:
        """
        Get a readable slugified version of the title or filename or content
        appropriate for this item. May not be unique.
        """
        title = self.abbrev_title(max_len=max_len)
        slug = slugify(title, max_length=max_len, separator="_")
        return slug

    def abbrev_description(self, max_len: int = 1000) -> str:
        """
        Get or infer description.
        """
        return abbrev_on_words(html_to_plaintext(self.description or self.body or ""), max_len)

    def read_as_config(self) -> Any:
        """
        If it is a config Item, return the parsed YAML.
        """
        if not self.type == ItemType.config:
            raise FileFormatError(f"Item is not a config: {self}")
        if not self.body:
            raise FileFormatError(f"Config item has no body: {self}")
        if self.format != Format.yaml:
            raise FileFormatError(f"Config item is not YAML: {self.format}: {self}")
        return from_yaml_string(self.body)

    def get_file_ext(self) -> FileExt:
        """
        Get or infer file extension.
        """
        if self.file_ext:
            return self.file_ext
        if self.is_binary and not self.file_ext:
            raise ValueError(f"Binary Items must have a file extension: {self}")
        inferred_ext = self.format and self.format.file_ext
        if not inferred_ext:
            raise ValueError(f"Cannot infer file extension for Item: {self}")
        return inferred_ext

    def get_full_suffix(self) -> str:
        """
        Get the full file extension suffix (e.g. "note.md") for this item.
        """

        if self.type == ItemType.extension:
            # Python files cannot have more than one . in them.
            return f"{FileExt.py.value}"
        elif self.type == ItemType.script:
            # Same for kash scripts.
            return f"{self.type.value}.{FileExt.ksh.value}"
        else:
            return f"{self.type.value}.{self.get_file_ext().value}"

    def full_text(self) -> str:
        """
        Get the full text of the item, including any title, description, and body.
        Use for embeddings.
        """
        parts = [self.title, self.description, self.body_text().strip()]
        return "\n\n".join(part for part in parts if part)

    def body_text(self) -> str:
        if self.is_binary:
            raise ValueError("Cannot get text content of a binary Item")
        return self.body or ""

    def body_as_html(self) -> str:
        if self.format == Format.html:
            return self.body_text()
        elif self.format == Format.plaintext:
            return plaintext_to_html(self.body_text())
        elif self.format == Format.markdown or self.format == Format.md_html:
            return markdown_to_html(self.body_text())

        raise ValueError(f"Cannot convert item of type {self.format} to HTML: {self}")

    def _copy_and_update(
        self, other: Item | None = None, update_timestamp: bool = False, **other_updates
    ) -> dict[str, Any]:
        overrides: dict[str, Any] = {"store_path": None, "modified_at": None}
        if update_timestamp:
            overrides["created_at"] = datetime.now()

        fields = deepcopy(self.__dict__)

        if other:
            other_fields = deepcopy(other.__dict__)
            fields.update(other_fields)
            fields["extra"] = {**(self.extra or {}), **(other.extra or {})}

        fields.update(overrides)
        fields.update(other_updates)

        return fields

    def new_copy_with(self, update_timestamp: bool = True, **other_updates) -> Item:
        """
        Copy item with the given field updates. Resets store_path to None. Updates
        created time if requested.
        """
        new_fields = self._copy_and_update(update_timestamp=update_timestamp, **other_updates)
        return Item(**new_fields)

    def merged_copy(self, other: Item) -> Item:
        """
        Copy item, merging in fields from another, with the other item's fields
        taking precedence. Resets store_path to None.
        """
        merged_fields = self._copy_and_update(other, update_timestamp=False)
        return Item(**merged_fields)

    def derived_copy(self, type: ItemType, **other_updates) -> Item:
        """
        Same as `new_copy_with()`, but also makes any other updates and updates the
        `derived_from` relation. If we also have an action context, then use the
        `title_template` to derive a new title.
        """
        if not self.store_path:
            if self.relations.derived_from:
                log.message(
                    "Deriving from an item that has not been saved so using "
                    "its derived_from relation: %s on %s",
                    self.relations.derived_from,
                    self,
                )
                derived_from: list[Locator] | None = self.relations.derived_from
            else:
                log.warning(
                    "Deriving from an item that has not been saved so cannot "
                    "record derived_from relation: %s",
                    self,
                )
                derived_from = None
        else:
            derived_from = [StorePath(self.store_path)]

        updates = other_updates.copy()
        updates["type"] = type

        # External resource paths only make sense for resources, so clear them out if new item
        # is not a resource.
        new_type = updates.get("type") or self.type
        if "external_path" not in updates and new_type != ItemType.resource:
            updates["external_path"] = None

        new_item = self.new_copy_with(update_timestamp=True, **updates)
        if derived_from:
            new_item.update_relations(derived_from=derived_from)

        # Fall back to action title template if we have it and it wasn't explicitly set.
        if "title" not in other_updates:
            if self.context:
                action = self.context.action
                new_item.title = action.title_template.format(
                    title=self.title or UNTITLED, action_name=action.name
                )
            else:
                log.warning("Deriving an item without action context, will omit title: %s", self)

        return new_item

    def update_relations(self, **relations: Sequence[Locator]) -> ItemRelations:
        """
        Update relations with the given field updates.
        """
        self.relations = self.relations or ItemRelations()
        for key, value in relations.items():
            setattr(self.relations, key, list(value))
        return self.relations

    def update_history(self, source: Source) -> None:
        """
        Update the history of the item with the given operation.
        """
        self.source = source
        self.add_to_history(source.operation.summary())

    def item_id(self) -> ItemId | None:
        """
        Return identity of the item, or None if it should be treated as unique.
        """
        return ItemId.for_item(self)

    def content_equals(self, other: Item) -> bool:
        """
        Check if two items have identical content, ignoring timestamps and store path.
        """
        # Check relevant metadata fields.
        self_fields = self.__dict__.copy()
        other_fields = other.__dict__.copy()
        for fields_dict in [self_fields, other_fields]:
            for f in ["created_at", "modified_at", "store_path", "body"]:
                fields_dict.pop(f, None)

        metadata_matches = self_fields == other_fields

        # Trailing newlines don't matter.
        body_matches = (
            self.is_binary == other.is_binary and self.body == other.body
        ) or self.body_text().rstrip() == other.body_text().rstrip()
        return metadata_matches and body_matches

    def add_to_history(self, operation_summary: OperationSummary):
        if not self.history:
            self.history = []
        # Don't add duplicates to the history.
        if not self.history or self.history[-1] != operation_summary:
            self.history.append(operation_summary)

    def fmt_loc(self) -> str:
        """
        Formatted store path, external path, or title. For error messages etc.
        """
        if self.store_path:
            return fmt_store_path(self.store_path)
        elif self.external_path:
            return fmt_loc(self.external_path)
        else:
            return repr(self.abbrev_title())

    def as_chat_history(self) -> ChatHistory:
        if self.type != ItemType.chat:
            raise ValueError(f"Expected chat item, got {self.type}")
        if not self.body:
            raise ValueError("Chat item has no body")
        return ChatHistory.from_yaml(self.body)

    def as_str_brief(self) -> str:
        return (
            abbrev_obj(
                self,
                key_filter={
                    "store_path": 0,
                    "type": 64,
                    "title": 64,
                    "url": 64,
                    "external_path": 64,
                    "context": 64,
                },
            )
            + f"[{len(self.body) if self.body else 0} body chars]"
        )

    def as_str(self) -> str:
        return (
            abbrev_obj(
                self,
                key_filter={
                    "store_path": 0,
                    "external_path": 64,
                    "type": 64,
                    "state": 64,
                    "title": 64,
                    "url": 64,
                    "format": 64,
                    "created_at": 64,
                    "body": 64,
                    "context": 64,
                },
            )
            + f"[{len(self.body) if self.body else 0} body chars]"
        )

    def __repr__(self):
        return self.as_str_brief()


# Some reflection magic so the order of the YAML metadata for an item will match
# the order of the fields here.
ITEM_FIELDS = [f.name for f in Item.__dataclass_fields__.values()]


## Tests


def test_item_metadata_serialization():
    # Important to confirm StorePath is serialized like a Path.
    ir = ItemRelations(derived_from=[StorePath("docs/filename.doc.md")])
    assert asdict(ir) == {
        "cites": None,
        "derived_from": [StorePath("docs/filename.doc.md")],
        "diff_of": None,
    }
