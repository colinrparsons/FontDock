#!/usr/bin/env python3
"""One-time script to normalize ALL CAPS font family names to title case."""
import requests

BASE = "http://localhost:9998"

# Login
print("Logging in...")
login = requests.post(f"{BASE}/auth/login", data={"username": "admin", "password": "admin"})
token = login.json()["access_token"]

# Normalize
print("Normalizing family names...")
resp = requests.post(f"{BASE}/api/fonts/normalize-family-names", headers={"Authorization": f"Bearer {token}"})
print(resp.json())
