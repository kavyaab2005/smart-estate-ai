import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text


engine = create_engine(os.getenv("DATABASE_URL"))
conn = engine.connect()
r = conn.execute(text("SELECT id FROM properties WHERE status != 'pending' LIMIT 1"))
row = r.fetchone()
conn.execute(text("UPDATE properties SET status = :s WHERE id = :i"), {"s": "pending", "i": str(row.id)})
conn.commit()
print("Flipped:", row.id)