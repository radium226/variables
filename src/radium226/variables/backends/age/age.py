from pathlib import Path
from contextlib import contextmanager
from subprocess import run
from typing import Generator, TypeAlias
from loguru import logger
from textwrap import dedent
import sys

from ...files import create_temp_file

from .types import KeyPair, Passphrase
from .key_pair import load_key_pair, find_key_pair
from .passphrase import find_passphrase



Config: TypeAlias = KeyPair | Passphrase


class Age():

    config: Config

    def __init__(self, config: Config) -> None:
        self.config = config


    def encrypt_value(self, decrypted_value: bytes) -> bytes:
        if isinstance(key_pair := self.config, KeyPair):
            logger.debug("Spawning age with key pair encryption... ")
            command = [
                "age", 
                "--encrypt", 
                "--recipient", str(key_pair.public_key),
                "-o", "-",
                "-"
            ]
            process = run(command, input=decrypted_value, capture_output=True)
            print(process.stderr, file=sys.stderr)
            return process.stdout
        
        if isinstance(passphrase := self.config, str):
            logger.debug("Spawning age (through expect) with passphrase encryption... ")
            expect_script_content = dedent(r"""
                set timeout -1
                set log_user 0
                set encrypted_file [lindex $argv 0]
                set decrypted_file [lindex $argv 1]
                set passphrase [lindex $argv 2]
                spawn age --encrypt --passphrase -o "$encrypted_file" "$decrypted_file"
                expect "Enter passphrase*"
                send "$passphrase\r"
                expect "Confirm passphrase*"
                send "$passphrase\r"
                expect eof  
            """)
            with create_temp_file(content=decrypted_value) as decrypted_value_file_path:
                with create_temp_file() as encrypted_value_file_path:
                    with create_temp_file(content=expect_script_content) as expect_script_file_path:
                        command = [
                            "expect",
                            "-f", str(expect_script_file_path),
                            str(encrypted_value_file_path),
                            str(decrypted_value_file_path),
                            passphrase,
                        ]
                        process = run(command, check=True)
                        return encrypted_value_file_path.read_bytes()

        raise Exception("Invalid key pair or passphrase.")
    

    def decrypt_value(self, encrypted_value: bytes) -> bytes:
        if isinstance(key_pair := self.config, KeyPair):
            logger.debug("Spawning age with key pair decryption... ")
            private_key = key_pair.private_key
            with create_temp_file(content=private_key) as private_key_file_path:
                command = [
                    "age", 
                    "--decrypt",
                    "--identity", str(private_key_file_path),
                    "-o", "-",
                    "-"
                ]
                process = run(command, input=encrypted_value, capture_output=True)
                print(process.stderr)
                return process.stdout
            
        if isinstance(passphrase := self.config, str):
            logger.debug("Spawning age (through expect) with passphrase decryption... ")
            expect_script_content = dedent(r"""
                set timeout -1
                set log_user 0
                set encrypted_file [lindex $argv 0]
                set decrypted_file [lindex $argv 1]
                set passphrase [lindex $argv 2]
                spawn age --decrypt -o "$decrypted_file" "$encrypted_file"
                expect "Enter passphrase*"
                send "$passphrase\r"
                send "\004"
                expect eof                            
            """)

            with create_temp_file(content=encrypted_value) as encrypted_value_file_path:
                with create_temp_file() as decrypted_value_file_path:
                    with create_temp_file(content=expect_script_content) as expect_script_file_path:
                        command = [
                            "expect",
                            "-f", str(expect_script_file_path),
                            str(encrypted_value_file_path),
                            str(decrypted_value_file_path),
                            passphrase,
                        ]
                        process = run(command, check=True)
                        return decrypted_value_file_path.read_bytes()
        
        raise Exception("Invalid key pair or passphrase.")


def parse_config(obj: dict[str, str]) -> Config:
    key_pair: KeyPair | None = None
    if "key_pair" in obj:
        logger.info("Using key pair! ")
        key_pair = load_key_pair(Path(obj["key_pair"]))
    else:
        key_pair = find_key_pair()

    passphrase: Passphrase | None = None
    if "passphrase" in obj:
        logger.info("Using passphrase! ")
        passphrase = obj["passphrase"]
    else:
        passphrase = find_passphrase()

    config: Config | None = passphrase or key_pair
    if config is None:
        raise Exception("No valid key pair or passphrase found in the configuration.")
    return config


@contextmanager
def create_backend(config: Config) -> Generator[Age, None, None]:
    yield Age(config)