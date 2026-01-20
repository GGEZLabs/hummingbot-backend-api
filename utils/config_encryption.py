"""
Utility functions for encrypting and decrypting secure fields in configurations.

This module provides functions to:
- Identify secure fields from Pydantic config classes (fields with SecretStr type or is_secure=True)
- Encrypt secure fields before saving to YAML
- Decrypt secure fields when loading from YAML
- Mask secure fields for display in list views
"""
import logging
from typing import Any, Dict, Optional, Set, Type

from hummingbot.client.config.config_crypt import ETHKeyFileSecretManger
from pydantic import SecretStr

from config import settings
from utils.file_system import fs_util

logger = logging.getLogger(__name__)


def get_secrets_manager() -> ETHKeyFileSecretManger:
    """Get the secrets manager instance with the configured password."""
    return ETHKeyFileSecretManger(password=settings.security.config_password)


def get_secure_fields_from_config_class(config_class: Optional[Type]) -> Set[str]:
    """
    Extract field names that are marked as secure from a Pydantic config class.

    A field is considered secure if:
    - Its type annotation is SecretStr
    - Its json_schema_extra contains is_secure=True

    Args:
        config_class: The Pydantic model class to inspect

    Returns:
        Set of field names that should be encrypted
    """
    if config_class is None:
        return set()

    secure_fields = set()
    for field_name, field_info in config_class.model_fields.items():
        # Check if field type is SecretStr
        if field_info.annotation == SecretStr:
            secure_fields.add(field_name)
        # Check json_schema_extra for is_secure flag
        if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
            if field_info.json_schema_extra.get("is_secure", False):
                secure_fields.add(field_name)
    return secure_fields


def get_secure_fields_for_script(script_name: str) -> Set[str]:
    """
    Get secure fields for a script by loading its config class.

    Args:
        script_name: Name of the script (without .py extension)

    Returns:
        Set of field names that should be encrypted
    """
    config_class = fs_util.load_script_config_class(script_name)
    return get_secure_fields_from_config_class(config_class)


def get_secure_fields_for_controller(controller_type: str, controller_name: str) -> Set[str]:
    """
    Get secure fields for a controller by loading its config class.

    Args:
        controller_type: Type of the controller (e.g., 'directional_trading', 'market_making')
        controller_name: Name of the controller (without .py extension)

    Returns:
        Set of field names that should be encrypted
    """
    config_class = fs_util.load_controller_config_class(controller_type, controller_name)
    return get_secure_fields_from_config_class(config_class)


def encrypt_secure_fields(config: Dict[str, Any], secure_fields: Set[str]) -> Dict[str, Any]:
    """
    Encrypt fields that are marked as secure.

    Args:
        config: Configuration dictionary with clear text values
        secure_fields: Set of field names to encrypt

    Returns:
        New config dictionary with encrypted values for secure fields
    """
    if not secure_fields:
        return config

    secrets_manager = get_secrets_manager()
    encrypted_config = config.copy()

    for field_name in secure_fields:
        if field_name in encrypted_config and encrypted_config[field_name]:
            clear_value = encrypted_config[field_name]
            # Only encrypt if it's a string and not empty
            if isinstance(clear_value, str) and clear_value:
                encrypted_value = secrets_manager.encrypt_secret_value(field_name, clear_value)
                encrypted_config[field_name] = encrypted_value
                logger.info(f"Encrypted secure field: {field_name}")

    return encrypted_config


def decrypt_secure_fields(config: Dict[str, Any], secure_fields: Set[str]) -> Dict[str, Any]:
    """
    Decrypt fields that are marked as secure.

    Args:
        config: Configuration dictionary with encrypted values
        secure_fields: Set of field names to decrypt

    Returns:
        New config dictionary with decrypted values for secure fields
    """
    if not secure_fields:
        return config

    secrets_manager = get_secrets_manager()
    decrypted_config = config.copy()

    for field_name in secure_fields:
        if field_name in decrypted_config and decrypted_config[field_name]:
            encrypted_value = decrypted_config[field_name]
            if isinstance(encrypted_value, str) and encrypted_value:
                try:
                    decrypted_value = secrets_manager.decrypt_secret_value(field_name, encrypted_value)
                    decrypted_config[field_name] = decrypted_value
                except Exception as e:
                    # If decryption fails, the value might not be encrypted (legacy data)
                    logger.warning(f"Could not decrypt field {field_name}: {e}")

    return decrypted_config


def mask_secure_fields(config: Dict[str, Any], secure_fields: Set[str], mask: str = "********") -> Dict[str, Any]:
    """
    Mask secure fields for display purposes (e.g., in list views).

    Args:
        config: Configuration dictionary
        secure_fields: Set of field names to mask
        mask: The mask string to use (default: "********")

    Returns:
        New config dictionary with masked values for secure fields
    """
    if not secure_fields:
        return config

    masked_config = config.copy()
    for field_name in secure_fields:
        if field_name in masked_config and masked_config[field_name]:
            masked_config[field_name] = mask

    return masked_config
