from sqlalchemy import create_engine, text
import bcrypt

# Connect to database
engine = create_engine('sqlite:///fontdock.db')

with engine.connect() as conn:
    # Get admin user details
    result = conn.execute(text("SELECT id, username, password_hash, is_active FROM users WHERE username = 'admin'"))
    row = result.fetchone()
    
    if row:
        user_id, username, password_hash, is_active = row
        print(f"User ID: {user_id}")
        print(f"Username: {username}")
        print(f"Is Active: {is_active}")
        print(f"Password hash: {password_hash}")
        print(f"Hash length: {len(password_hash) if password_hash else 0}")
        
        # Try to verify password
        if password_hash:
            try:
                plain_bytes = 'admin123'.encode('utf-8')
                hash_bytes = password_hash.encode('utf-8')
                result = bcrypt.checkpw(plain_bytes, hash_bytes)
                print(f"Password verify result: {result}")
            except Exception as e:
                print(f"Verify error: {e}")
                
            # Generate a new hash and verify it
            print("\n--- Generating new hash ---")
            salt = bcrypt.gensalt()
            new_hash = bcrypt.hashpw('admin123'.encode('utf-8'), salt)
            print(f"New hash: {new_hash.decode('utf-8')}")
            
            # Update database with new hash
            conn.execute(
                text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"),
                {"hash": new_hash.decode('utf-8')}
            )
            conn.commit()
            print("Updated password in database")
    else:
        print("Admin user not found!")
