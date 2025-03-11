from pathlib import Path

from kash.file_storage.persisted_yaml import PersistedYaml
from kash.model.params_model import RawParamValues


class ParamState:
    """
    Persist global parameters for a workspace.
    """

    def __init__(self, yaml_file: Path):
        self.params = PersistedYaml(yaml_file, init_value={})

    def set(self, action_params: dict):
        """Set a global parameter for this workspace."""
        self.params.save(action_params)

    def get_raw_values(self) -> RawParamValues:
        """Get any parameters set globally for this workspace."""
        try:
            return RawParamValues(self.params.read())
        except OSError:
            return RawParamValues({})
