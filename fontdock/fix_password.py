from sqlalchemy import create_engine, text
from passlib.context import CryptContext

# Password hash
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password_hash = pwd_context.hash('admin123')

print(f"Generated hash: {password_hash}")

# Update database
engine = create_engine('sqlite:///fontdock.db')
with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"),
        {"hash": password_hash}
    )
    conn.commit()
    print(f"Updated {result.rowcount} user(s)")

# Verify
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT password_hash FROM users WHERE username = 'admin'")
    )
    row = result.fetchone()
    if row:
        stored_hash = row[0]
        print(f"Stored hash: {stored_hash}")
        print(f"Verify: {pwd_context.verify('admin123', stored_hash)}")
