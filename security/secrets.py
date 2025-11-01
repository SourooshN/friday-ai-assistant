"""
Friday Volatile Secret Store

Manages secrets in volatile encrypted memory only.
"""

from typing import Any, Dict, Optional

from cryptography.fernet import Fernet

from core.logging import get_logger


class SecretStore:
    """
    Volatile secret store that keeps secrets only in encrypted memory.

    Secrets are never written to disk and are lost when the process exits.
    This is a security feature per the specifications.
    """

    def __init__(self, security_config: Dict[str, Any]):
        self.config = security_config
        self.logger = get_logger()

        # Generate a random key for this session
        self._key = Fernet.generate_key()
        self._cipher = Fernet(self._key)

        # In-memory encrypted storage
        self._encrypted_secrets: Dict[str, bytes] = {}

        self.logger.info("Volatile secret store initialized")
        self.logger.audit("Secret store initialized", action="secret_store_init")

    def store_secret(self, key: str, value: str) -> bool:
        """
        Store a secret in volatile encrypted memory.

        Args:
            key: Secret identifier
            value: Secret value

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Encrypt the secret value
            encrypted_value = self._cipher.encrypt(value.encode("utf-8"))

            # Store in memory
            self._encrypted_secrets[key] = encrypted_value

            self.logger.debug(f"Secret stored: {key}")
            self.logger.audit("Secret stored", action="secret_store", key=key)

            return True

        except Exception as e:
            self.logger.error(f"Failed to store secret {key}: {e}")
            return False

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret from volatile encrypted memory.

        Args:
            key: Secret identifier

        Returns:
            Decrypted secret value or None if not found
        """
        try:
            if key not in self._encrypted_secrets:
                return None

            # Decrypt the secret value
            encrypted_value = self._encrypted_secrets[key]
            decrypted_value = self._cipher.decrypt(encrypted_value)

            self.logger.debug(f"Secret retrieved: {key}")
            self.logger.audit("Secret retrieved", action="secret_retrieve", key=key)

            return decrypted_value.decode("utf-8")

        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {key}: {e}")
            return None

    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret from volatile memory.

        Args:
            key: Secret identifier

        Returns:
            True if deleted successfully, False if not found
        """
        if key in self._encrypted_secrets:
            del self._encrypted_secrets[key]
            self.logger.debug(f"Secret deleted: {key}")
            self.logger.audit("Secret deleted", action="secret_delete", key=key)
            return True

        return False

    def has_secret(self, key: str) -> bool:
        """
        Check if a secret exists.

        Args:
            key: Secret identifier

        Returns:
            True if secret exists, False otherwise
        """
        return key in self._encrypted_secrets

    def list_secret_keys(self) -> list[str]:
        """
        Get a list of all secret keys (not values).

        Returns:
            List of secret keys
        """
        return list(self._encrypted_secrets.keys())

    def clear_all(self):
        """Clear all secrets from memory."""
        count = len(self._encrypted_secrets)
        self._encrypted_secrets.clear()

        # Also clear the encryption key for extra security
        self._key = None
        self._cipher = None

        self.logger.info(f"Cleared {count} secrets from volatile store")
        self.logger.audit("All secrets cleared", action="secret_clear_all", count=count)

    def get_status(self) -> Dict[str, Any]:
        """Get secret store status."""
        return {
            "initialized": self._cipher is not None,
            "secret_count": len(self._encrypted_secrets),
            "keys": list(self._encrypted_secrets.keys()),  # Keys only, never values
        }
