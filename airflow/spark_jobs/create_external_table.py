import os
import sys
from pyspark.sql import SparkSession

# If command-line arguments are provided, use them to set environment variables.
# Expected order: [script_name, AZURE_STORAGE_ACCOUNT, AZURE_CONTAINER]
if len(sys.argv) > 2:
    os.environ["AZURE_STORAGE_ACCOUNT"] = sys.argv[1]
    os.environ["AZURE_CONTAINER"] = sys.argv[2]
    os.environ["FILE_NAME"] = sys.argv[3]

# Now retrieve the variables (they might have been set by operator arguments or
# already exist in the Synapse env )
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT")
AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER")
parquet_file = os.environ.get("FILE_NAME")

spark = SparkSession.builder.appName('CreateExternalTable').getOrCreate()

spark.sql(f"""
    CREATE EXTERNAL TABLE green_tripdata
    WITH(
        LOCATION = 'https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_CONTAINER}/raw/{parquet_file}',
        DATA_SOURCE = 'AzureBlobStorage',
        FILE_FORMAT = 'PARQUET'
    )
""")
spark.stop()
