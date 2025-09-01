import logging
from typing import Dict, List

from hummingbot.client.config.client_config_map import ClientConfigMap
from hummingbot.client.config.config_helpers import ClientConfigAdapter

from utils.file_system import fs_util

# Create module-specific logger
logger = logging.getLogger(__name__)


class ClientConfManager:
    def __init__(self): ...

    def _list_config_folders(self, account_name: str) -> List[str]:
        """
        List all configuration files in the given folder path.

        Args:
            conf_folder_path (str): The path to the configuration folder.

        Returns:
            list: A list of configuration file names.
        """
        try:
            conf_folder_path = f"credentials/{account_name}/configs/"
            return fs_util.list_folders(conf_folder_path)
        except Exception as e:
            logger.error(f"Error listing client configuration files: {e}")
            raise

    def list_configs(self, account_name: str) -> list[str]:
        """
        List all configuration folders names for a given account.

        Returns:
            list: A dictionary containing the list of client configuration files.
        """
        try:
            return self._list_config_folders(account_name)
        except Exception as e:
            logger.error(f"Error listing client configuration files: {e}")
            raise

    def get_client_config_by_name(self, account_name: str, config_name: str) -> Dict:
        """
        Retrieve the client configuration for a specific config name.

        Returns:
            Dict: The client configuration as a dictionary.
        """
        conf_file_path = f"credentials/{account_name}/configs/{config_name}/conf_client.yml"
        try:
            # config = ClientConfigAdapter(fs_util.read_yaml_file(conf_file_path))
            return fs_util.read_yaml_file(conf_file_path)
        except Exception as e:
            logger.error(f"Error retrieving client configuration: {e}")
            raise

    def update_client_config_by_name(self, account_name: str, config_name: str, client_config: Dict) -> Dict:
        """
        Update the client configuration for a specific config name.

        Returns:
            Dict: A dictionary containing the updated client configuration.
        """
        client_conf_file_path = f"credentials/{account_name}/configs/{config_name}/conf_client.yml"
        try:
            if config_name not in self._list_config_folders(account_name):
                raise FileNotFoundError(f"Config folder '{config_name}' not found for account '{account_name}'.")
            # fs_util.dump_dict_to_yaml(client_conf_file_path, client_config)
            _client_config = ClientConfigMap(**client_config)
            config_map = ClientConfigAdapter(_client_config)
            fs_util.save_model_to_yml(client_conf_file_path, config_map)
            return {"client_config": client_config}
        except Exception as e:
            logger.error(f"Error retrieving client configuration: {e}")
            raise

    def add_config_folder(self, account_name: str, config_name: str) -> None:
        # Check if config already exists by looking at folders
        if config_name in self._list_config_folders(account_name):
            raise FileExistsError(f"Config {config_name} already exists. for account {account_name}")

        files_to_copy = [
            "conf_client.yml",
            "conf_fee_overrides.yml",
            "hummingbot_logs.yml",
        ]
        fs_util.create_folder(f"credentials/{account_name}/configs", config_name)
        for file in files_to_copy:
            fs_util.copy_file(
                f"credentials/master_account/configs/default/{file}", f"credentials/{account_name}/configs/{config_name}/{file}"
            )

    def delete_config_folder(self, account_name: str, config_name: str) -> None:
        """
        Delete a configuration folder for a given account.

        Args:
            account_name (str): The name of the account.
            config_name (str): The name of the configuration folder to delete.

        Raises:
            FileNotFoundError: If the configuration folder does not exist.
        """
        if config_name not in self._list_config_folders(account_name):
            raise FileNotFoundError(f"Config folder '{config_name}' not found for account '{account_name}'.")
        if config_name == "default":
            raise ValueError("Cannot delete default config folder.")

        conf_folder_path = f"credentials/{account_name}/configs/"
        try:
            fs_util.delete_folder(conf_folder_path, config_name)
        except Exception as e:
            logger.error(f"Error deleting configuration folder: {e}")
            raise


"""

TODO
Add Config Folder Structure
    Create a configs subfolder inside each credential folder (e.g., credentials/{account_name}/configs/).
    Each config is a folder or file (e.g., credentials/{account_name}/configs/{config_name}/conf_client.yml).

Function to Add a Config Folder
    Implement a function to create a new config folder for a given credential/account.
    Optionally, copy default config files into the new config folder.

Function to List Configs
    Implement a function to list all config folders for a given credential/account.

Function to Update a Config File
    Implement a function to update a specific config file (e.g., conf_client.yml) inside a specified config folder.

Function to Delete a Config Folder
    Implement a function to delete a specific config folder for a credential/account.

Update Bot Launch Logic
    Modify bot launching to require both a credential (account) and a config name.
    When launching, load configs from credentials/{account_name}/configs/{config_name}/.

Update API/Service Methods
    Update relevant API endpoints and service methods to support config selection and management.

Migration Script (Optional)
    If you have existing configs, write a script to move them into the new structure.
"""
