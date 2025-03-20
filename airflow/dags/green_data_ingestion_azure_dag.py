import os
import logging
import requests
import io
import json

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.microsoft.azure.operators.synapse import AzureSynapseRunSparkBatchOperator

# Import custom Key Vault hook
from hooks.azure_key_vault_hook import AzureKeyVaultHook

# Import Azure Key Vault libaries for secret retrieval
# from azure.identity import ClientSecretCredential
# from azure.keyvault.secrets import SecretClient

from azure.storage.blob import BlobServiceClient
#from azure.synapse.spark import SparkSession
import pyarrow.csv as pv
import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd

# Environment variables for Key Vault authentication and URL
# AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
# AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
# KEY_VAULT_URL = os.environ.get("KEY_VAULT_URL")

# Spark configuration values
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER')
SYNAPSE_WORKSPACE_NAME = os.environ.get('SYNAPSE_WORKSPACE_NAME')
SYNAPSE_SPARK_POOL_NAME = os.environ.get('SYNAPSE_SPARK_POOL_NAME')

dataset_file = "green_tripdata.parquet"
dataset_url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2022-01.parquet"
path_to_local_home = os.environ.get("AIRFLOW_HOME", "/opt/airflow/")
parquet_file = dataset_file.replace('.csv', '.parquet')

def format_to_parquet(src_file):
    if not src_file.endswith('.csv'):
        logging.error("Can only accept source files in CSV format, for the moment")
        return
    table = pv.read_csv(src_file)
    pq.write_table(table, src_file.replace('.csv', '.parquet'))

def download_data_and_concat():
    pq_writer = None
    
    for i in range(1,13):
        padded_i = str(i).zfill(2)
        
        url = f'https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2022-{padded_i}.parquet' 
        print(f"Requesting URL: {url}")
        
        #Download the parquet file into memory
        response = requests.get(url)
        response.raise_for_status()

        #Read the parquet from bytes into a PyArrow Table
        table = pq.read_table(io.BytesIO(response.content))
        #Write incrementally to the final parquet file
        if pq_writer is None:
            pq_writer = pq.ParquetWriter(f"{path_to_local_home}/{dataset_file}", table.schema)

        pq_writer.write_table(table)

    if pq_writer:
        pq_writer.close()

# Connection string retrieved from Key Vault.
azure_kv_hook = AzureKeyVaultHook()
AZURE_STORAGE_CONNECTION_STRING = azure_kv_hook.get_secret("azure-storage-connection-string")

def upload_to_azure(container_name, blob_name, local_file):
    """
    Uploads a file to Azure Blob Storage
    """

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    with open(local_file, "rb") as data:
        blob_client.upload_blob(data)

# def create_external_table():
#     """
#     Create an external table in Azure Synapse Analytics.
#     """

#     spark = SparkSession.builder \
#         .appName("CreateExternalTable") \
#         .getOrCreate()

#     spark.sql(f"""
#         CREATE EXTERNAL TABLE green_tripdata
#         WITH (
#             LOCATION = 'https://{os.environ.get("AZURE_STORAGE_ACCOUNT")}.blob.core.windows.net/{AZURE_CONTAINER}/raw/{parquet_file}',
#             DATA_SOURCE = 'AzureBlobStorage',
#             FILE_FORMAT = 'PARQUET'
#         )
#     """)

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "depends_on_past": False,
    "retries": 1,
}

# NOTE: DAG declaration - using a Context Manager (an implicit way)
with DAG(
    dag_id="green_data_ingestion_azure_dag",
    schedule_interval="@daily",
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=['dtc-de'],
    params={
        "parquet_file": parquet_file,
    },
) as dag:

    download_dataset_task = PythonOperator(
        task_id="download_dataset_task",
        python_callable=download_data_and_concat,
        #bash_command=f"curl -sSL {dataset_url} > {path_to_local_home}/{dataset_file}"
    )

    local_to_azure_task = PythonOperator(
        task_id="local_to_azure_task",
        python_callable=upload_to_azure,
        op_kwargs={
            "container_name": AZURE_CONTAINER,
            "blob_name": f"raw/{parquet_file}",
            "local_file": f"{path_to_local_home}/{parquet_file}",
        },
    )

    # create_external_table_task = PythonOperator(
    #     task_id='create_external_table_task',
    #     python_callable=create_external_table,
    # )

        #synapse_workspace_name = "{{ var.value.SYNAPSE_WORKSPACE_NAME }}",
    create_external_table_task = AzureSynapseRunSparkBatchOperator(
        task_id = 'create_external_table_task',
        azure_synapse_conn_id='azure_synapse_default',
        synapse_pool_name = "{{ var.value.SYNAPSE_SPARK_POOL_NAME }}",
        payload={
            "file": 'abfss://{{ var.value.AZURE_CONTAINER }}/spark_jobs/create_external_table.py',
            "class_name": 'CreateExternalTableJob',
            "args": [
                '{{ var.value.AZURE_STORAGE_ACCOUNT }}',
                '{{ var.value.AZURE_CONTAINER }}',
                '{{ params.parquet_file}}',
            ]
        },
    )

    download_dataset_task >> local_to_azure_task >> create_external_table_task # format_to_parquet_task