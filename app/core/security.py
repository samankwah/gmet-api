# """
# Security utilities for API key management.

# This module contains functions for hashing and verifying API keys using bcrypt.
# """

# import secrets
# from passlib.context import CryptContext

# # Create bcrypt context for API key hashing
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def generate_api_key_plaintext() -> str:
#     """
#     Generate a secure random API key.

#     Returns:
#         32-character hexadecimal string (16 bytes = 32 hex chars)
#         Note: bcrypt has a 72-byte limit, so we keep this under that limit
#     """
#     return secrets.token_hex(16)


# def hash_api_key(plain_key: str) -> str:
#     """
#     Hash an API key using bcrypt.

#     Uses bcrypt for secure API key hashing with automatic salt generation.

#     Args:
#         plain_key: Plain text API key

#     Returns:
#         Bcrypt hashed API key string
#     """
#     return pwd_context.hash(plain_key)


# def verify_api_key(plain_key: str, stored_hash: str) -> bool:
#     """
#     Verify a plain text API key against a stored bcrypt hash.

#     Args:
#         plain_key: Plain text API key to verify
#         stored_hash: Stored bcrypt hash

#     Returns:
#         True if the key matches, False otherwise
#     """
#     return pwd_context.verify(plain_key, stored_hash)




"""
Security utilities for password hashing and verification.
"""
import secrets
import bcrypt


def generate_api_key_plaintext() -> str:
    """
    Generate a secure random API key.

    Returns:
        32-character hexadecimal string (16 bytes = 32 hex chars)
        Note: bcrypt has a 72-byte limit, so we keep this under that limit
    """
    return secrets.token_hex(16)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')


def verify_api_key(plain_key: str, stored_hash: str) -> bool:
    """Verify an API key against its hash using bcrypt."""
    try:
        return bcrypt.checkpw(
            plain_key.encode('utf-8'), 
            stored_hash.encode('utf-8')
        )
    except Exception:
        return False


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt."""
    return bcrypt.hashpw(
        api_key.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')