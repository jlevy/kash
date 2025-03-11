from pathlib import Path
from typing import Any, List, Tuple

from frontmatter_format import read_yaml_file, write_yaml_file

from kash.util.obj_replace import remove_values, replace_values


class PersistedYaml:
    """
    Maintain simple data (such as a dictionary or list of strings) as a YAML file.
    File writes are atomic but does not lock.
    """

    def __init__(self, filename: str | Path, init_value: Any):
        self.filename = str(filename)
        self.initialize(init_value)

    def read(self) -> Any:
        return read_yaml_file(self.filename)

    def save(self, value: Any):
        write_yaml_file(value, self.filename)

    def initialize(self, value: Any):
        if not Path(self.filename).exists():
            self.save(value)

    def remove_values(self, targets: List[Any]):
        value = self.read()
        new_value = remove_values(value, targets)
        self.save(new_value)

    def replace_values(self, replacements: List[Tuple[Any, Any]]):
        value = self.read()
        new_value = replace_values(value, replacements)
        self.save(new_value)
