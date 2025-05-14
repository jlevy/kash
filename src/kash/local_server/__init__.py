from pathlib import Path

from kash.exec.importing import import_and_register

import_and_register(__package__, Path(__file__).parent, ["local_server_commands"])
