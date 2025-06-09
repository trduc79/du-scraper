# pylint: disable=import-error, import-outside-toplevel, unused-import
import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential  # type: ignore
from azure.keyvault.secrets import SecretClient  # type: ignore


def get_azure_blob_client(account_id=None, default_container=None, credentials=None):
    account_id = account_id or os.environ["AZURE_STORAGE_ACCOUNT_ID"]
    default_container = default_container or os.environ["AZURE_DEFAULT_CONTAINER"]

    if not credentials:
        credentials = DefaultAzureCredential()

    azure_client = AzureHandler(
        account_id, default_container=default_container, credentials=credentials
    )
    return azure_client


def get_client_secret(
    secret_name: str,
    vault_url: str,
):
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    client_secret = client.get_secret(secret_name).value
    return client_secret


def get_access_token(tenant_id, client_id, client_secret, api_token_endpoint):\
    credentials = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    access_token = credentials.get_token(api_token_endpoint)

    return access_token


