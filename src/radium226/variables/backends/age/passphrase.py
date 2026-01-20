from pathlib import Path
from loguru import logger
import os

from .types import Passphrase



def find_passphrase() -> Passphrase | None:
    if os.getenv("VARIABLES_PASSPHRASE") is not None:
        return os.getenv("VARIABLES_PASSPHRASE")

    folder_path = Path.cwd()
    while True:
        if (passphrase_file_path := folder_path / "variables.passphrase").exists():
            return passphrase_file_path.read_text(encoding="utf-8")
        
        if ( folder_path / ".git" ).exists():
            logger.warning("Reached the git root folder without finding a 'variables.passphrase' file.")
            break

        folder_path = folder_path.parent

    return None