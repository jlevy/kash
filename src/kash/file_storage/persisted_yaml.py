from pathlib import Path
from typing import Any

from frontmatter_format import read_yaml_file, write_yaml_file
from funlog import log_calls

from kash.utils.common.obj_replace import remove_values, replace_values


class PersistedYaml:
    """
    Maintain simple data (such as a dictionary or list of strings) as a YAML file.
    File writes are atomic but does not lock.
    """

    def __init__(self, filename: str | Path, init_value: Any):
        self.filename = str(filename)
        self.initialize(init_value)

    @log_calls(level="warning", if_slower_than=2.0)  # Helpful to flag slow disk I/O.
    def read(self) -> Any:
        return read_yaml_file(self.filename)

    def save(self, value: Any):
        write_yaml_file(value, self.filename)

    def initialize(self, value: Any):
        if not Path(self.filename).exists():
            self.save(value)

    def remove_values(self, targets: list[Any]):
        value = self.read()
        new_value = remove_values(value, targets)
        self.save(new_value)

    def replace_values(self, replacements: list[tuple[Any, Any]]):
        value = self.read()
        new_value = replace_values(value, replacements)
        self.save(new_value)

    def __repr__(self):
        return f"PersistedYaml({self.filename!r})"

    __str__ = __repr__
