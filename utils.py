from typing import Tuple
from pysodium import crypto_sign_keypair, crypto_sign_detached


def gen_keypair() -> Tuple[bytes, bytes]:
    return crypto_sign_keypair()


def sign(data: bytes, sk: bytes) -> bytes:
    return crypto_sign_detached(data, sk)


def encode(bytes):
    return codecs.encode(bytes, "hex").decode("utf-8")
