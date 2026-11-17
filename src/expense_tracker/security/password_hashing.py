import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_password_hasher = PasswordHasher()


async def hash_password(password: str) -> str:
    """
    Hash the password with Argon2id in a worker thread.
    """
    return await asyncio.to_thread(_password_hasher.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    """
    Check the password against the hash in a worker thread.
    """
    try:
        return await asyncio.to_thread(_password_hasher.verify, password_hash, password)
    except VerifyMismatchError, InvalidHashError:
        return False
