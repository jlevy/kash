from pathlib import Path
from typing import Any

from kash.file_storage.persisted_yaml import PersistedYaml
from kash.model.params_model import RawParamValues


class ParamState:
    """
    Persist global parameters for a workspace.
    """

    def __init__(self, yaml_file: Path) -> None:
        self.params = PersistedYaml(yaml_file, init_value={})

    def set(self, action_params: dict[str, Any]) -> None:
        """Set parameters for this workspace."""
        self.params.save(action_params)

    def get_raw_values(self) -> RawParamValues:
        """Get any parameters set globally for this workspace."""
        try:
            return RawParamValues(self.params.read())
        except OSError:
            return RawParamValues({})
