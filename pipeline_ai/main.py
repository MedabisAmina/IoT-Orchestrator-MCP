def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="pipeline_db",
        user="iotuser",
        password="iotfrontier"
    )