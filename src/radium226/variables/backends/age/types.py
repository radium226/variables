from dataclasses import dataclass
from typing import TypeAlias


PrivateKey: TypeAlias = str


PublicKey: TypeAlias = str


@dataclass(frozen=True, eq=True)
class KeyPair:
    private_key: PrivateKey
    public_key: PublicKey



Passphrase: TypeAlias = str