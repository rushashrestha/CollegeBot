import pandas as pd
import hashlib
from supabase import create_client, Client
import os
import requests # Need this for the Admin API calls

# 🚨🚨 CRITICAL CHANGE 🚨🚨
# You MUST use the Service Role Key, NOT the Anon Key.
# Find this key under Project Settings -> API Keys (it will be labeled as 'service_role key').
 # This loads the variables from the .env file into the config dictionary
config = dotenv_values(".env")

# Retrieve the keys from the config dictionary
SUPABASE_URL = config.get("SUPABASE_URL")
# CRITICAL: Use the service role key for administrative access
SUPABASE_SERVICE_ROLE_KEY = config.get("SUPABASE_SERVICE_ROLE_KEY")

# Base URL for the GoTrue (Auth) Admin API
AUTH_ADMIN_URL = f"{SUPABASE_URL}/auth/v1/admin/users"

# ⚠️ REMOVE THE HASHING FUNCTION: The Auth Admin API expects a PLAIN-TEXT password.
# def hash_password(password):
#     """Hash password using SHA-256"""
#     return hashlib.sha256(str(password).encode()).hexdigest()

def send_auth_admin_request(email, password, full_name, role):
    """
    Sends a request to the Supabase Auth Admin API to create a user.
    This creates the user in the internal 'auth.users' table.
    """
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_ROLE_KEY
    }
    
    payload = {
        "email": email,
        "password": password, # 🚨 Must be plain-text for this API
        "email_confirm": True, # Automatically confirm the email to allow immediate login
        "user_metadata": {
            "full_name": full_name,
            "role": role # Store custom data here
        }
    }
    
    try:
        response = requests.post(AUTH_ADMIN_URL, json=payload, headers=headers)
        response.raise_for_status() # Raise exception for 4xx or 5xx errors
        return None
    except requests.exceptions.HTTPError as e:
        # Supabase returns errors like 409 Conflict if user already exists
        return e.response.json().get('msg') or str(e)
    except Exception as e:
        return str(e)


def import_users(filename, role_name):
    """Generic function to import users from a file into Auth system."""
    print("\n" + "="*60)
    print(f"🔄 MIGRATING {role_name.upper()} USERS TO SUPABASE AUTH")
    print("="*60)
    
    try:
        df = pd.read_excel(filename)
        print(f"✅ Found {len(df)} {role_name}s in {filename}\n")
        
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            email = str(row['Email']).strip().lower()
            password = str(row['Password']).strip() # 🚨 Get the PLAIN-TEXT password
            full_name = str(row['Name']).strip()
            
            # 1. Attempt to create the user in the secure auth.users table
            auth_error = send_auth_admin_request(email, password, full_name, role_name)

            if auth_error:
                error_count += 1
                print(f"❌ Error on row {index + 2} ({email}): {auth_error}")
            else:
                # 2. Optionally, insert the metadata into your custom public.users table (optional)
                #    We skip this for simplicity in a migration, but you may need it if
                #    your public.users table has critical extra fields (like student_id).
                #    If you *do* need to insert, you MUST get the user UID from the 
                #    response of send_auth_admin_request to link the tables correctly.
                
                success_count += 1
                print(f"✅ [{success_count}] {full_name} - {email}")

        print("\n" + "="*60)
        print(f"✅ Successfully migrated: {success_count} {role_name}s")
        print(f"❌ Errors (Skipped): {error_count} {role_name}s")
        print("="*60)
        
        return success_count, error_count
        
    except FileNotFoundError:
        print(f"❌ ERROR: {filename} not found!")
        return 0, 0
    except Exception as e:
        print(f"❌ GENERIC ERROR: {str(e)}")
        return 0, 0

# ⚠️ REMOVE THE HASH_PASSWORD function and the original 'import_students' and 'import_teachers'

def verify_database():
    """Check how many users are in the database"""
    print("\n" + "="*60)
    print("🔍 VERIFYING AUTH.USERS TABLE")
    print("="*60)
    
    # We can't easily query the Auth table roles from the Python library's main client.
    # The simplest way to verify the migration is to check the Supabase Dashboard
    # under Authentication -> Users.
    print("Please check your Supabase Dashboard under 'Authentication -> Users' for verification.")
    print("This script is unable to query the internal auth.users table roles directly.")
    print("="*60)

def main():
    # ... (rest of main function remains the same, but call the new import_users)
    print("\n")
    print("🚀 " + "="*56 + " 🚀")
    print("   SUPABASE USER MIGRATION SCRIPT - ASKSAMRIDDHI")
    print("🚀 " + "="*56 + " 🚀")
    
    # Check if Supabase credentials are set
    if SUPABASE_SERVICE_ROLE_KEY == "YOUR_SUPABASE_SERVICE_ROLE_KEY" or SUPABASE_URL == "YOUR_SUPABASE_URL":
        print("\n❌ ERROR: Please update SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the script!")
        print("   Get the Service Role Key from: Supabase Dashboard -> Settings -> API")
        return
        
    # Check if files exist
    files_exist = True
    if not os.path.exists('students.xlsx'):
        print("❌ students.xlsx not found!")
        files_exist = False
    else:
        print("✅ students.xlsx found")
    
    if not os.path.exists('teachers.xlsx'):
        print("❌ teachers.xlsx not found!")
        files_exist = False
    else:
        print("✅ teachers.xlsx found")
    
    if not files_exist:
        print("\n⚠️  Please place both Excel files in the backend folder!")
        return
    
    # Confirm before proceeding
    print(f"\n⚠️  This will migrate data into the secure AUTH system of: {SUPABASE_URL}")
    print("⚠️  It requires the plain-text passwords from your Excel files.")
    confirm = input("\n👉 Type 'yes' to continue with MIGRATION: ").lower()
    
    if confirm != 'yes':
        print("❌ Migration cancelled.")
        return
    
    # Call the new, single import function
    student_success, student_errors = import_users('students.xlsx', 'student')
    teacher_success, teacher_errors = import_users('teachers.xlsx', 'teacher')
    
    # Verify the import
    verify_database()
    
    print("\n✅ Migration process completed!\n")

if __name__ == "__main__":
    main()