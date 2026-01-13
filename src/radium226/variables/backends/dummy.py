from contextlib import contextmanager
from typing import Generator

class Config():
    pass


def parse_config(config: dict[str, str]) -> Config:
    return Config()


class Dummy():

    def encrypt_value(self, decrypted_value: bytes) -> bytes:
        return decrypted_value

    def decrypt_value(self, encrypted_value: bytes) -> bytes:
        return encrypted_value


@contextmanager
def create_backend(config: Config) -> Generator[Dummy, None, None]:
    yield Dummy()