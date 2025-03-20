import logging

from airflow.hooks.base import BaseHook
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

class AzureKeyVaultHook(BaseHook):
    """
    A custom Airflow Hook to retrieve secrets from Azure Key Vault.
    Expects an Airflow connection with conn_id = azure_key_vault (or any name you choose)
    where:
         - The 'Extras' JSON or specialized fields store key_vault_url, tenant_id, client_id
         - The 'Password' field may store client_secret (if not using managed identity)
    """

    def __init__(self, azure_key_vault_conn_id: str = "azure_key_vault") -> None:
        super().__init__()
        self.conn_id = azure_key_vault_conn_id
        self.conn = self.get_connection(self.conn_id) # retrieve from Airflow Connection
        self.extra = self.conn.extra_dejson

        # Pull Key Vault URL and non-sensitive config from connection 'Extra'
        self.key_vault_url = self.extra.get("key_vault_url")
        self.tenant_id = self.extra.get("tenant_id")
        self.client_id = self.extra.get("client_id")

        # If the client secret is stored in the connection's 'Password' field:
        self.client_secret = self.conn.password

        # Create Azure credential & secret client
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.secret_client = SecretClient(vault_url=self.key_vault_url, credential=self.credential)

    def get_secret(self, secret_name: str) -> str:
        """
        Retrieve a secret's value from Key Vault.
        """
        self.log.info(f"Fetching secret '{secret_name}' from Key Vault: {self.key_vault_url}")
        secret = self.secret_client.get_secret(secret_name)
        return secret.value