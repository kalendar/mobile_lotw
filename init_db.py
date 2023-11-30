import os
import psycopg2

conn = psycopg2.connect(
        host="localhost",
        database="mobile_lotw",
        user=os.environ['DB_USERNAME'],
        password=os.environ['DB_PASSWORD'])

# Open a cursor to perform database operations
cur = conn.cursor()

cur.execute('CREATE TABLE qsls ('
    'id serial PRIMARY KEY,'
    'op varchar (120) NOT NULL,'
    'worked varchar (120) NOT NULL,'
    'band varchar (120) NOT NULL,'
    'mode varchar (120) NOT NULL,'
    'details varchar (150) NOT NULL);'
    )

cur.execute('CREATE TABLE qsls_email ('
    'id serial PRIMARY KEY,'
    'op varchar (120) NOT NULL,'
    'worked varchar (120) NOT NULL,'
    'band varchar (120) NOT NULL,'
    'mode varchar (120) NOT NULL,'
    'details varchar (150) NOT NULL);'
    )

conn.commit()

cur.close()
conn.close()
