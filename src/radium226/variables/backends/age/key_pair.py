from typing import overload
from pathlib import Path
from re import Pattern
import re
from loguru import logger

from .types import PrivateKey, PublicKey, KeyPair



PRIVATE_KEY_PATTERN: Pattern = re.compile(r"^(?P<private_key>AGE-SECRET-KEY-[A-Z0-9]+)$")



PUBLIC_KEY_PATTERN: Pattern = re.compile(r"^# public key: (?P<public_key>age[a-z0-9]+)$")



@overload
def load_key_pair(text: str, /) -> KeyPair: ...



@overload
def load_key_pair(file_path: Path, /) -> KeyPair: ...



def load_key_pair(text_or_file_path: str | Path, /) -> KeyPair:
    if isinstance(text_or_file_path, Path):
        text = text_or_file_path.read_text(encoding="utf-8")
    else:
        text = text_or_file_path

    private_key: PrivateKey | None = None
    public_key: PublicKey | None = None
    for line in text.splitlines():
        line = line.strip()
        if match := PRIVATE_KEY_PATTERN.match(line):
            private_key = match.group("private_key")
        elif match := PUBLIC_KEY_PATTERN.match(line):
            public_key = match.group("public_key")
        
    assert private_key is not None, "Private key not found in the provided text."
    assert public_key is not None, "Public key not found in the provided text."
    return KeyPair(
        private_key=private_key, 
        public_key=public_key
    )


def find_key_pair() -> KeyPair | None:
    folder_path = Path.cwd()
    while True:
        if (key_pair_file_path := folder_path / "variables.key").exists():
            return load_key_pair(key_pair_file_path)
        
        if ( folder_path / ".git" ).exists():
            logger.warning("Reached the git root folder without finding a 'variables.key' file.")
            break

        folder_path = folder_path.parent

    return None