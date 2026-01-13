from dataclasses import dataclass


type PrivateKey = str


type PublicKey = str


@dataclass(frozen=True, eq=True)
class KeyPair:
    private_key: PrivateKey
    public_key: PublicKey



type Passphrase = str