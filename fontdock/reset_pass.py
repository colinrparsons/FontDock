import bcrypt
from sqlalchemy import create_engine, text

# Generate proper bcrypt hash
password = b'admin123'
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password, salt)
hash_str = hashed.decode('utf-8')

print(f"Generated bcrypt hash: {hash_str}")

# Update database
engine = create_engine('sqlite:///fontdock.db')
with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"),
        {"hash": hash_str}
    )
    conn.commit()
    print(f"Updated {result.rowcount} row(s)")
    
    # Verify update
    result = conn.execute(
        text("SELECT password_hash FROM users WHERE username = 'admin'")
    )
    row = result.fetchone()
    if row:
        stored = row[0]
        print(f"Stored hash: {stored}")
        # Verify it works
        verify = bcrypt.checkpw(password, stored.encode('utf-8'))
        print(f"Verification: {verify}")
