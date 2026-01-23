"""
Cryptographic Utilities for Sync.

Provides encryption/decryption utilities for secure sync operations.
"""

import logging
import os
import base64
from typing import Optional, Union, BinaryIO
from pathlib import Path
import hashlib
import hmac
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.exceptions import InvalidKey, InvalidTag

logger = logging.getLogger(__name__)


class SyncCrypto:
    """
    Cryptographic utilities for sync operations.

    Provides encryption/decryption of files and data for secure sync.
    Uses AES-256-GCM for authenticated encryption.
    """

    # Key derivation parameters
    SALT_SIZE = 32
    KEY_SIZE = 32  # 256 bits
    IV_SIZE = 12   # 96 bits for GCM
    TAG_SIZE = 16  # 128 bits

    def __init__(self, password: Optional[str] = None, key_file: Optional[str] = None):
        """
        Initialize crypto utilities.

        Args:
            password: Password for key derivation (optional)
            key_file: Path to file containing encryption key (optional)
        """
        self.password = password
        self.key_file = key_file
        self._derived_key: Optional[bytes] = None

        # Load or derive key
        if key_file and Path(key_file).exists():
            self._load_key_from_file(key_file)
        elif password:
            self._derive_key_from_password(password)
        else:
            logger.warning("No password or key file provided - encryption disabled")

    def _derive_key_from_password(self, password: str):
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: User password
        """
        try:
            # Generate salt
            salt = os.urandom(self.SALT_SIZE)

            # Key derivation
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.KEY_SIZE,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )

            self._derived_key = kdf.derive(password.encode('utf-8'))

            # Store salt for later use
            self._salt = salt

            logger.info("Derived encryption key from password")

        except Exception as e:
            logger.error(f"Failed to derive key from password: {e}")
            self._derived_key = None

    def _load_key_from_file(self, key_file: str):
        """
        Load encryption key from file.

        Args:
            key_file: Path to key file
        """
        try:
            with open(key_file, 'rb') as f:
                key_data = f.read()

            if len(key_data) != self.KEY_SIZE:
                raise ValueError(f"Key file must contain exactly {self.KEY_SIZE} bytes")

            self._derived_key = key_data
            logger.info(f"Loaded encryption key from file: {key_file}")

        except Exception as e:
            logger.error(f"Failed to load key from file {key_file}: {e}")
            self._derived_key = None

    def save_key_to_file(self, key_file: str):
        """
        Save the current encryption key to a file.

        Args:
            key_file: Path to save key file
        """
        if not self._derived_key:
            raise ValueError("No encryption key available to save")

        try:
            Path(key_file).parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(self._derived_key)
            logger.info(f"Saved encryption key to file: {key_file}")

        except Exception as e:
            logger.error(f"Failed to save key to file {key_file}: {e}")
            raise

    def is_encryption_enabled(self) -> bool:
        """
        Check if encryption is enabled.

        Returns:
            True if encryption key is available
        """
        return self._derived_key is not None

    def encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM.

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data with IV and tag
        """
        if not self._derived_key:
            raise ValueError("Encryption key not available")

        try:
            # Generate IV
            iv = os.urandom(self.IV_SIZE)

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self._derived_key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Encrypt data
            ciphertext = encryptor.update(data) + encryptor.finalize()

            # Combine IV + tag + ciphertext
            encrypted_data = iv + encryptor.tag + ciphertext

            return encrypted_data

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM.

        Args:
            encrypted_data: Encrypted data (IV + tag + ciphertext)

        Returns:
            Decrypted data
        """
        if not self._derived_key:
            raise ValueError("Encryption key not available")

        if len(encrypted_data) < self.IV_SIZE + self.TAG_SIZE:
            raise ValueError("Encrypted data too short")

        try:
            # Extract components
            iv = encrypted_data[:self.IV_SIZE]
            tag = encrypted_data[self.IV_SIZE:self.IV_SIZE + self.TAG_SIZE]
            ciphertext = encrypted_data[self.IV_SIZE + self.TAG_SIZE:]

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self._derived_key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext

        except InvalidTag:
            raise ValueError("Authentication failed - data may be corrupted or wrong key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_file(self, input_path: Union[str, Path], output_path: Union[str, Path]):
        """
        Encrypt a file.

        Args:
            input_path: Path to input file
            output_path: Path to output encrypted file
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        try:
            # Read input file
            with open(input_path, 'rb') as f:
                data = f.read()

            # Encrypt data
            encrypted_data = self.encrypt_data(data)

            # Write encrypted file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)

            logger.debug(f"Encrypted file: {input_path} -> {output_path}")

        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise

    def decrypt_file(self, input_path: Union[str, Path], output_path: Union[str, Path]):
        """
        Decrypt a file.

        Args:
            input_path: Path to input encrypted file
            output_path: Path to output decrypted file
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        try:
            # Read encrypted file
            with open(input_path, 'rb') as f:
                encrypted_data = f.read()

            # Decrypt data
            decrypted_data = self.decrypt_data(encrypted_data)

            # Write decrypted file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

            logger.debug(f"Decrypted file: {input_path} -> {output_path}")

        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise

    def generate_file_hash(self, file_path: Union[str, Path]) -> str:
        """
        Generate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        try:
            sha256 = hashlib.sha256()

            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            logger.error(f"Failed to generate file hash: {e}")
            raise

    def generate_data_hash(self, data: bytes) -> str:
        """
        Generate SHA-256 hash of data.

        Args:
            data: Data to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()

    def generate_hmac(self, data: bytes, key: Optional[bytes] = None) -> str:
        """
        Generate HMAC-SHA256 of data.

        Args:
            data: Data to authenticate
            key: HMAC key (uses encryption key if not provided)

        Returns:
            Hexadecimal HMAC string
        """
        hmac_key = key or self._derived_key
        if not hmac_key:
            raise ValueError("No key available for HMAC")

        hmac_obj = hmac.new(hmac_key, data, hashlib.sha256)
        return hmac_obj.hexdigest()

    def verify_hmac(self, data: bytes, expected_hmac: str, key: Optional[bytes] = None) -> bool:
        """
        Verify HMAC-SHA256 of data.

        Args:
            data: Data to verify
            expected_hmac: Expected HMAC string
            key: HMAC key (uses encryption key if not provided)

        Returns:
            True if HMAC matches
        """
        hmac_key = key or self._derived_key
        if not hmac_key:
            raise ValueError("No key available for HMAC verification")

        calculated_hmac = self.generate_hmac(data, hmac_key)
        return hmac.compare_digest(calculated_hmac, expected_hmac)

    def encrypt_json(self, data: dict) -> str:
        """
        Encrypt a JSON-serializable object.

        Args:
            data: Data to encrypt

        Returns:
            Base64-encoded encrypted data
        """
        import json
        json_str = json.dumps(data, sort_keys=True)
        encrypted = self.encrypt_data(json_str.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt_json(self, encrypted_b64: str) -> dict:
        """
        Decrypt a JSON object.

        Args:
            encrypted_b64: Base64-encoded encrypted data

        Returns:
            Decrypted JSON data
        """
        import json
        encrypted = base64.b64decode(encrypted_b64)
        decrypted = self.decrypt_data(encrypted)
        return json.loads(decrypted.decode('utf-8'))

    def get_key_info(self) -> dict:
        """
        Get information about the current encryption key.

        Returns:
            Key information
        """
        if not self._derived_key:
            return {'enabled': False}

        return {
            'enabled': True,
            'key_size': len(self._derived_key) * 8,
            'algorithm': 'AES-256-GCM',
            'key_source': 'password' if self.password else 'file' if self.key_file else 'unknown'
        }

    @classmethod
    def generate_key_file(cls, key_file: str, password: Optional[str] = None):
        """
        Generate a new encryption key file.

        Args:
            key_file: Path to save key file
            password: Optional password for key derivation
        """
        if password:
            # Derive key from password
            crypto = cls(password=password)
            crypto.save_key_to_file(key_file)
        else:
            # Generate random key
            key = os.urandom(cls.KEY_SIZE)
            Path(key_file).parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info(f"Generated random encryption key file: {key_file}")


class EncryptedSyncProvider:
    """
    Wrapper for sync providers that adds encryption/decryption.
    """

    def __init__(self, provider, crypto: SyncCrypto):
        """
        Initialize encrypted sync provider.

        Args:
            provider: Base sync provider
            crypto: Crypto utilities instance
        """
        self.provider = provider
        self.crypto = crypto

    async def upload_file(self,
                         local_path: Union[str, Path],
                         remote_path: str,
                         metadata: Optional[dict] = None) -> bool:
        """
        Upload an encrypted file.

        Args:
            local_path: Local file path
            remote_path: Remote storage path
            metadata: Optional metadata

        Returns:
            True if upload successful
        """
        if not self.crypto.is_encryption_enabled():
            # Fall back to unencrypted upload
            return await self.provider.upload_file(local_path, remote_path, metadata)

        try:
            # Create temporary encrypted file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

            # Encrypt file
            self.crypto.encrypt_file(local_path, temp_path)

            # Upload encrypted file
            success = await self.provider.upload_file(temp_path, remote_path, metadata)

            # Clean up
            Path(temp_path).unlink(missing_ok=True)

            return success

        except Exception as e:
            logger.error(f"Encrypted upload failed: {e}")
            return False

    async def download_file(self,
                           remote_path: str,
                           local_path: Union[str, Path]) -> bool:
        """
        Download and decrypt a file.

        Args:
            remote_path: Remote storage path
            local_path: Local file path

        Returns:
            True if download successful
        """
        if not self.crypto.is_encryption_enabled():
            # Fall back to unencrypted download
            return await self.provider.download_file(remote_path, local_path)

        try:
            # Create temporary file for encrypted download
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

            # Download encrypted file
            success = await self.provider.download_file(remote_path, temp_path)
            if not success:
                Path(temp_path).unlink(missing_ok=True)
                return False

            # Decrypt file
            self.crypto.decrypt_file(temp_path, local_path)

            # Clean up
            Path(temp_path).unlink(missing_ok=True)

            return True

        except Exception as e:
            logger.error(f"Encrypted download failed: {e}")
            return False

    # Delegate other methods to the wrapped provider
    async def connect(self) -> bool:
        return await self.provider.connect()

    async def disconnect(self):
        await self.provider.disconnect()

    async def is_connected(self) -> bool:
        return await self.provider.is_connected()

    async def delete_file(self, remote_path: str) -> bool:
        return await self.provider.delete_file(remote_path)

    async def list_files(self, remote_path: str = "", recursive: bool = False):
        return await self.provider.list_files(remote_path, recursive)

    async def get_file_info(self, remote_path: str):
        return await self.provider.get_file_info(remote_path)

    async def create_directory(self, remote_path: str) -> bool:
        return await self.provider.create_directory(remote_path)

    async def delete_directory(self, remote_path: str) -> bool:
        return await self.provider.delete_directory(remote_path)

    def get_provider_info(self):
        info = self.provider.get_provider_info()
        info['encrypted'] = self.crypto.is_encryption_enabled()
        return info