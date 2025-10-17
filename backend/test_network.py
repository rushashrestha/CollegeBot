import requests
import json

# Your credentials
SUPABASE_URL = "https://yzyxfjnyvwxegcdkhcpl.supabase.co"  

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl6eXhmam55dnd4ZWdjZGtoY3BsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk5MjQ0MjgsImV4cCI6MjA3NTUwMDQyOH0.Ve7v45A0LfXRfz-YPoZDXVKPfrDzHi3s0cZSer60ujc"

print("="*60)
print("🔍 SUPABASE CONNECTION DEBUG")
print("="*60)

# Test 1: Basic connection
print("\n1️⃣ Testing basic connection...")
try:
    response = requests.get(SUPABASE_URL, timeout=5)
    print(f"   ✅ Connection successful! Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit()

# Test 2: Test REST API endpoint
print("\n2️⃣ Testing REST API endpoint...")
url = f"{SUPABASE_URL}/rest/v1/"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

try:
    response = requests.get(url, headers=headers, timeout=5)
    print(f"   ✅ REST API accessible! Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit()

# Test 3: Check if users table exists
print("\n3️⃣ Checking if 'users' table exists...")
url = f"{SUPABASE_URL}/rest/v1/users"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers, timeout=5)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ Table exists! Found {len(response.json())} records")
    elif response.status_code == 404:
        print(f"   ❌ Table 'users' not found!")
        print(f"   Response: {response.text}")
    elif response.status_code == 401:
        print(f"   ❌ Authentication failed! Check your anon key")
        print(f"   Response: {response.text}")
    else:
        print(f"   ⚠️  Unexpected response: {response.text}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit()

# Test 4: Try inserting a test record
print("\n4️⃣ Testing insert operation...")
url = f"{SUPABASE_URL}/rest/v1/users"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

test_data = {
    "email": "test@example.com",
    "password": "hashed_password_test",
    "role": "student",
    "full_name": "Test User",
    "student_id": "TEST001"
}

try:
    response = requests.post(url, json=test_data, headers=headers, timeout=5)
    print(f"   Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        print(f"   ✅ Insert successful!")
        print(f"   Response: {response.json()}")
    elif response.status_code == 409:
        print(f"   ⚠️  Duplicate record (test user already exists)")
    else:
        print(f"   ❌ Insert failed!")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 5: Clean up test record
print("\n5️⃣ Cleaning up test record...")
url = f"{SUPABASE_URL}/rest/v1/users?email=eq.test@example.com"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

try:
    response = requests.delete(url, headers=headers, timeout=5)
    if response.status_code in [200, 204]:
        print(f"   ✅ Cleanup successful!")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Cleanup failed: {e}")

print("\n" + "="*60)
print("✅ DEBUG COMPLETE")
print("="*60)
print("\nIf all tests passed, the import should work!")
print("If any failed, check the error messages above.")