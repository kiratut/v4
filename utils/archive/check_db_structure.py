# // TEMP: Quick DB structure analysis
import sqlite3

conn = sqlite3.connect('data/hh_v4.sqlite3')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

# Check vacancies table structure
for table in tables:
    if 'vacanc' in table.lower():
        print(f'\n=== Table: {table} ===')
        cursor.execute(f'PRAGMA table_info({table})')
        cols = cursor.fetchall()
        for col in cols:
            nullable = "NULL" if not col[3] else "NOT NULL"
            pk = " PK" if col[5] else ""
            print(f'  {col[1]:20} {col[2]:15} {nullable:8} {pk}')
        
        # Sample data
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'  Records: {count}')

conn.close()
