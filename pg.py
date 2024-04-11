import os
import argparse

import psycopg
import pyarrow.parquet as pq
from pgvector.psycopg import register_vector


def read_parquet_file(file_path):
    table = pq.read_table(file_path)
    df = table.to_pandas()
    lst = df.values.tolist()
    return lst

if __name__ == "__main__":
    parser = argparse.ArgumentParser() 
    parser.add_argument("--query", action="store_true", help="Whether to run a query on the collection")
    parser.add_argument("--ingest", action="store_true", help="Whether to ingest the embeddings into the collection")
    args = parser.parse_args()

    conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/vectordb", autocommit=True)
    print("Connected to PostgreSQL: ", conn)

    if args.ingest:
        conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
        register_vector(conn)
        print("Initiated extension: pg_vector")

        conn.execute('DROP TABLE IF EXISTS embeddings_table')
        conn.execute('CREATE TABLE embeddings_table (id bigserial PRIMARY KEY, content text, embedding vector(1536))')
        print("Created table: embeddings_table")

        file_list = os.listdir("dbpedia-entities-openai-1M/data")
        row_idx = 0
        for file in file_list:
            batch = read_parquet_file(os.path.join("dbpedia-entities-openai-1M/data", file))
            for row in batch:
                conn.execute('INSERT INTO embeddings_table (content, embedding) VALUES (%s, %s)', (row[2], row[3]))        
                print(f"Inserted row {row_idx} into pg_vector")
                row_idx += 1

        print(f"Inserted {row_idx} rows into pg_vector")

    if args.query:
        file_list = os.listdir("dbpedia-entities-openai-1M/data")[5:15]
        for file in file_list:
            batch = read_parquet_file(os.path.join("dbpedia-entities-openai-1M/data", file))
            for row in batch:
                embedding_str = ','.join(str(x) for x in row[3])
                print(f"Running query for vector: [{embedding_str}]")
                conn.execute("SELECT * FROM embeddings_table ORDER BY embedding <-> '[%s]' LIMIT 5;", (embedding_str))
                print(conn.fetchall())
