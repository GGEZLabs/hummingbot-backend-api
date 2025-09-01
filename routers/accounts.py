from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from deps import get_accounts_service
from services.accounts_service import AccountsService

router = APIRouter(tags=["Accounts"], prefix="/accounts")


@router.get("/", response_model=List[str])
async def list_accounts(accounts_service: AccountsService = Depends(get_accounts_service)):
    """
    Get a list of all account names in the system.

    Returns:
        List of account names
    """
    return accounts_service.list_accounts()


@router.get("/{account_name}/credentials", response_model=List[str])
async def list_account_credentials(account_name: str, accounts_service: AccountsService = Depends(get_accounts_service)):
    """
    Get a list of all connectors that have credentials configured for a specific account.

    Args:
        account_name: Name of the account

    Returns:
        List of connector names that have credentials configured

    Raises:
        HTTPException: 404 if account not found
    """
    try:
        credentials = accounts_service.list_credentials(account_name)
        # Remove .yml extension from filenames
        return [cred.replace(".yml", "") for cred in credentials]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-account", status_code=status.HTTP_201_CREATED)
async def add_account(account_name: str, accounts_service: AccountsService = Depends(get_accounts_service)):
    """
    Create a new account with default configuration files.

    Args:
        account_name: Name of the new account to create

    Returns:
        Success message when account is created

    Raises:
        HTTPException: 400 if account already exists
    """
    try:
        accounts_service.add_account(account_name)
        return {"message": "Account added successfully."}
    except FileExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete-account")
async def delete_account(account_name: str, accounts_service: AccountsService = Depends(get_accounts_service)):
    """
    Delete an account and all its associated credentials.

    Args:
        account_name: Name of the account to delete

    Returns:
        Success message when account is deleted

    Raises:
        HTTPException: 400 if trying to delete master account, 404 if account not found
    """
    try:
        if account_name == "master_account":
            raise HTTPException(status_code=400, detail="Cannot delete master account.")
        await accounts_service.delete_account(account_name)
        return {"message": "Account deleted successfully."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/delete-credential/{account_name}/{connector_name}")
async def delete_credential(
    account_name: str, connector_name: str, accounts_service: AccountsService = Depends(get_accounts_service)
):
    """
    Delete a specific connector credential for an account.

    Args:
        account_name: Name of the account
        connector_name: Name of the connector to delete credentials for

    Returns:
        Success message when credential is deleted

    Raises:
        HTTPException: 404 if credential not found
    """
    try:
        await accounts_service.delete_credentials(account_name, connector_name)
        return {"message": "Credential deleted successfully."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/add-credential/{account_name}/{connector_name}", status_code=status.HTTP_201_CREATED)
async def add_credential(
    account_name: str, connector_name: str, credentials: Dict, accounts_service: AccountsService = Depends(get_accounts_service)
):
    """
    Add or update connector credentials (API keys) for a specific account and connector.

    Args:
        account_name: Name of the account
        connector_name: Name of the connector
        credentials: Dictionary containing the connector credentials

    Returns:
        Success message when credentials are added

    Raises:
        HTTPException: 400 if there's an error adding the credentials
    """
    try:
        await accounts_service.add_credentials(account_name, connector_name, credentials)
        return {"message": "Connector credentials added successfully."}
    except Exception as e:
        await accounts_service.delete_credentials(account_name, connector_name)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{account_name}/configs", response_model=List[str])
async def list_account_configs(account_name: str, accounts_service: AccountsService = Depends(get_accounts_service)):
    """
    Get a list of all configs names for account.

    Returns:
        List of account names
    """
    return accounts_service.list_account_configs(account_name)


@router.get("/{account_name}/config/{config_name}", response_model=Dict)
async def get_account_config_by_name(
    account_name: str, config_name: str, accounts_service: AccountsService = Depends(get_accounts_service)
):
    """
    Get a account client config by name of config folder for a specific account.

    Args:
        account_name: Name of the account
        config_name: Name of the config folder
    Returns:
        config

    Raises:
        HTTPException: 404 if account not found
    """
    try:
        client_config = accounts_service.get_account_client_config_by_name(account_name, config_name)
        return {"client_config": client_config}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_name}/update-config", response_model=Dict)
async def update_account_client_config_by_name(
    account_name: str, config_name: str, client_config: Dict, accounts_service: AccountsService = Depends(get_accounts_service)
):
    """
    Update client config for a specific account and config folder.

    Args:
        account_name: Name of the account
        config_name: Name of the config folder

    Returns:
        config

    Raises:
        HTTPException: 404 if account not found
    """
    try:
        client_config = accounts_service.update_account_client_config_by_name(
            account_name, config_name, client_config["client_config"]
        )
        return {"message": "Config updated successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_name}/add-config", response_model=None)
async def add_new_config_to_account(
    account_name: str, config_name: str, accounts_service: AccountsService = Depends(get_accounts_service)
):
    """
    add new config folder for a specific account.

    Args:
        account_name: Name of the account
        config_name: Name of the config folder

    Returns:
        None

    Raises:
        HTTPException: 404 if account not found
    """
    try:
        accounts_service.add_new_config_to_account(account_name, config_name)
        return {"message": "Config added successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_name}/delete-config", response_model=None)
async def delete_config_folder_from_account(
    account_name: str, config_name: str, accounts_service: AccountsService = Depends(get_accounts_service)
):
    """
    delete config folder for a specific account.

    Args:
        account_name: Name of the account
        config_name: Name of the config folder

    Returns:
        None

    Raises:
        HTTPException: 404 if account not found
    """
    try:
        accounts_service.delete_config_folder_from_account(account_name, config_name)
        return {"message": "Config deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
