import sqlite3
import re

# Define database paths
original_db_path = "data/arvo.db"
new_db_path = "data/crash.db"

# Connect to the original database
conn = sqlite3.connect(original_db_path)
cursor = conn.cursor()

# Fetch crash_output and other selected columns from the original database
cursor.execute(r"SELECT localId, project, sanitizer, report, fix_commit, repo_addr, crash_output FROM arvo WHERE "
               r"reproduced = 1 AND patch_located = 1 AND language='c++' AND submodule_bug = 0 AND fix_commit NOT LIKE CONCAT('%', CHAR(10), '%') AND repo_addr LIKE '%github.com%'")
rows = cursor.fetchall()
print(f"Fetched {len(rows)} rows from the original database.")

# Create a new database and table
new_conn = sqlite3.connect(new_db_path)
new_cursor = new_conn.cursor()
new_cursor.execute("""
    CREATE TABLE IF NOT EXISTS crash (
        localId INTEGER PRIMARY KEY,
        project TEXT,
        sanitizer TEXT,
        report TEXT,
        fix_commit TEXT,
        repo_addr TEXT,
        crash_output TEXT
    )
""")

# Remove ANSI escape sequences from crash_output and insert into the new database
count = 0
ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
for row in rows:
    local_id, project, sanitizer, report, fix_commit, repo_addr, crash_output = row
    clean_output = ansi_escape.sub("", crash_output)
    match = re.search(r"==\d+==", clean_output)
    if match:
        count += 1
        clean_output = clean_output[match.start():]
        clean_output = re.sub(r"==\d+==", "", clean_output)  # Remove all occurrences of the pattern
        clean_output = clean_output.strip()
        new_cursor.execute(
            "INSERT INTO crash (localId, project, sanitizer, report, fix_commit, repo_addr, crash_output) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (local_id, project, sanitizer, report, fix_commit, repo_addr, clean_output),
        )

print(f"Inserted {count} cleaned rows into the new database.")

new_conn.commit()
new_conn.close()
conn.close()