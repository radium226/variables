import pytest
from pytest import FixtureRequest
from typing import Generator
from pathlib import Path

from radium226.variables import Backend
from radium226.variables.backends import dummy
from radium226.variables.backends import age


@pytest.fixture
def backend(request: FixtureRequest) -> Generator[Backend, None, None]:
    match request.param:
        case "age-keypair":
            key_pair_file_path = Path(__file__).parent / "samples" / "age.key"
            
            with age.create_backend(age.parse_config({
                "key_pair": str(key_pair_file_path)}
            )) as backend:
                yield backend

        case "age-passphrase":
            with age.create_backend(age.parse_config({
                "passphrase": "my_secret_passphrase"
            })) as backend:
                yield backend
        
        case "dummy":
            with dummy.create_backend(dummy.parse_config({})) as backend:
                yield backend
        
        case _:
            raise ValueError(f"Unknown backend type: {request.param}")


@pytest.mark.parametrize(
    "backend", 
    [
        "age-keypair", 
        "age-passphrase", 
        "dummy",
    ], 
    indirect=True,
)
def test_backend(backend: Backend) -> None:
    value = "test_value"
    assert backend.decrypt_value(backend.encrypt_value(value.encode())) == value.encode("utf-8")