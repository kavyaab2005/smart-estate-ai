import os
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"]
parsed = urlparse(url)
print("Database host:", parsed.hostname)
print("Database name:", parsed.path)

conn = psycopg2.connect(url)
cur = conn.cursor()

cur.execute("select count(*) from properties")
print("Total rows in properties:", cur.fetchone()[0])

cur.execute("select status, count(*) from properties group by status order by 2 desc")
print("By status:", cur.fetchall())

cur.execute("select title, status from properties order by created_at desc nulls last limit 5")
print("Latest 5:")
for row in cur.fetchall():
    print("  ", row)

conn.close()