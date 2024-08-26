import os
import argparse
import pandas as pd
from time import time
from sqlalchemy import create_engine

def main(params):
    # USE THESE IF RUNNING SCRIPT VIA CLI
    # user = params.user
    # password = params.password
    # host = params.host
    # port = params.port
    # db = params.db
    # table_name = params.table_name
    # url = params.url
    
    #USE THESE ENV VARIABLES IF RUNNING VIA DOCKER COMPOSE DATA_INGESTION SERVICE
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT')
    db = os.getenv('POSTGRES_DB')
    table_name = os.getenv('TABLE_NAME')
    if params[0] == "yellow":
        url = os.getenv('DATA_URL_YELLOW')
        table_name = 'yellow_taxi_trips'
    elif params[0] == "green":
        url = os.getenv('DATA_URL_GREEN')
        table_name = 'green_taxi_trips'    
    elif params[0] == "zone":
        url = os.getenv('DATA_URL_ZONES')
        table_name = 'taxi_zones' 
    if not all([user, password, host, port, db, table_name, url]):
        raise ValueError("One or more environment variables are missing")

    # the backup files are gzipped, panda requires exact extension to open file
    if url.endswith('.csv.gz'):
        csv_name = "output.csv.gz"
    else:
        csv_name = "output.csv"

    os.system(f'wget {url} -O {csv_name}')

    engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{db}')

    engine.connect()

    df_iter = pd.read_csv(csv_name, iterator=True, chunksize=100000)

    while True:
        
        try:
            t_start = time()

            df = next(df_iter)

            if params[0] == "yellow":
                df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
                df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)

            df.to_sql(name=table_name, con=engine, if_exists='append')

            t_end = time()

            print('insert another chunk..., took %.3f seconds' %(t_end - t_start))
        
        except StopIteration:
            print("Finished ingesting data into the postgres database")
            break

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Ingest CSV data to Postgres')

    # USE THE ARGPARSE IF RUNNING SCRIPT FROM CLI
    # parser.add_argument('--user', required=True, help='user name for postgres')
    # parser.add_argument('--password', required=True, help='password name for postgres')
    # parser.add_argument('--host', required=True, help='host name for postgres')
    # parser.add_argument('--port', required=True, help='port name for postgres')
    # parser.add_argument('--db', required=True, help='db name for postgres')
    # parser.add_argument('--table_name', required=True, help='name of the table where we will write results to')
    # parser.add_argument('--url', required=True, help='url of the csv file')

    args = parser.parse_args()



    main(args)

