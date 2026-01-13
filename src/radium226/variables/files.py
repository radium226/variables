from contextlib import contextmanager
from typing import Generator
from tempfile import mkstemp
from pathlib import Path



@contextmanager
def create_temp_file(content: str | bytes | None = None) -> Generator[Path, None, None]:
    _, temp_file_path_str = mkstemp()
    temp_file_path = Path(temp_file_path_str)
    if content is not None:
        if isinstance(content, bytes):
            temp_file_path.write_bytes(content)
        else:
            temp_file_path.write_text(content, encoding="utf-8")
    try:
        yield temp_file_path
    finally:
        temp_file_path.unlink(missing_ok=True)