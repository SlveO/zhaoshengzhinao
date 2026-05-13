import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(32).hex()
    return f"{salt}:{hashlib.sha256((salt + password).encode()).hexdigest()}"


def verify_password(plain: str, hashed: str) -> bool:
    salt, hash_val = hashed.split(":", 1)
    return hashlib.sha256((salt + plain).encode()).hexdigest() == hash_val
