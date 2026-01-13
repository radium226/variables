from typing import Protocol, Callable, ContextManager, Any, cast
from importlib.metadata import entry_points, EntryPoint
from importlib import import_module
from dataclasses import dataclass



ENTRY_POINT_GROUP = "radium226.variables.backend"


class Config(Protocol):
    pass


type ParseConfig[T: Config] = Callable[[dict[str, str]], T]


type CreateBackend[T: Config] = Callable[[T], ContextManager[Backend]]


type Name = str

@dataclass
class Factory[T: Config]:

    name: Name
    parse_config: ParseConfig[T]
    create_backend: CreateBackend[T]


class Backend(Protocol):

    def encrypt_value(self, decrypted_value: bytes) -> bytes:
        ...

    def decrypt_value(self, encrypted_value: bytes) -> bytes:
        ...


def _create_factory(entry_point: EntryPoint) -> Factory[Any]:
    module_name = entry_point.value
    module = import_module(module_name)
    parse_config = cast(ParseConfig[Any], getattr(module, "parse_config"))
    create_backend = cast(CreateBackend[Any], getattr(module, "create_backend"))

    factory_name = entry_point.name
    return Factory(
        name=factory_name,
        parse_config=parse_config,
        create_backend=create_backend,
    )


def list_factories() -> list[Factory[Any]]:
    return [_create_factory(ep) for ep in entry_points(group=ENTRY_POINT_GROUP)]