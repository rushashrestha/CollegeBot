import pandas as pd
import requests
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

def parse_date(date_str):
    """Convert date string to proper format"""
    if pd.isna(date_str):
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str.strftime('%Y-%m-%d')
        return str(date_str).split()[0] if ' ' in str(date_str) else str(date_str)
    except:
        return None

def import_teachers_academic():
    """Import ALL teacher data for chatbot queries"""
    print("\n" + "="*60)
    print("👨‍🏫 IMPORTING TEACHER ACADEMIC DATA")
    print("="*60)
    
    try:
        df = pd.read_excel('teacherss.xlsx')
        df.columns = df.columns.str.strip()  # Remove extra spaces from headers
        print(f"✅ Found {len(df)} teachers")
        print("Columns detected:", df.columns.tolist(), "\n")
        
        success_count = 0
        error_count = 0
        
        url = f"{SUPABASE_URL}/rest/v1/teachers_data"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        for index, row in df.iterrows():
            try:
                teacher_data = {
                    'name': str(row.get('Name', '')).strip() or None,
                    'designation': str(row.get('Designation', '')).strip() or None,
                    'phone': str(row.get('Phone', '')).strip() or None,
                    'email': str(row.get('Email', '')).strip().lower() or None,
                    'address': str(row.get('Address', '')).strip() or None,
                    'degree': str(row.get('Degree', '')).strip() or None,
                    'subject': str(row.get('Subject', '')).strip() or None
                }

                # Skip rows without essential info like email
                if not teacher_data['email']:
                    error_count += 1
                    print(f"❌ Skipping row {index + 2}: missing email")
                    continue
                
                response = requests.post(url, json=teacher_data, headers=headers, timeout=10)
                
                if response.status_code in [200, 201]:
                    success_count += 1
                    print(f"✅ [{success_count}] {teacher_data['name']}")
                else:
                    error_count += 1
                    print(f"❌ [{error_count}] {teacher_data['name']}: {response.text}")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error on row {index + 2}: {str(e)}")
        
        print("\n" + "="*60)
        print(f"✅ Successfully imported: {success_count} teachers")
        print(f"❌ Errors: {error_count}")
        print("="*60)
        
        return success_count, error_count
        
    except FileNotFoundError:
        print("❌ teachers.xlsx not found!")
        return 0, 0
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 0, 0

def verify_data():
    """Verify imported data"""
    print("\n" + "="*60)
    print("🔍 VERIFYING IMPORTED DATA")
    print("="*60)
    
    try:
        # Check students
        url = f"{SUPABASE_URL}/rest/v1/students_data?select=count"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            count = len(response.json())
            print(f"👨‍🎓 Students in database: {count}")
        
        # Check teachers
        url = f"{SUPABASE_URL}/rest/v1/teachers_data?select=count"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            count = len(response.json())
            print(f"👨‍🏫 Teachers in database: {count}")
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error verifying: {str(e)}")

def main():
    print("\n🚀 " + "="*56 + " 🚀")
    print("   SUPABASE ACADEMIC DATA IMPORT")
    print("🚀 " + "="*56 + " 🚀\n")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Missing environment variables!")
        print("Make sure .env file has:")
        print("  SUPABASE_URL=...")
        print("  SUPABASE_ANON_KEY=...")
        return
    
    confirm = input("Import academic data? (yes/no): ").lower()
    if confirm != 'yes':
        print("❌ Cancelled")
        return
    
    # Import data
    import_teachers_academic()
    
    # Verify
    verify_data()
    
    print("\n✅ Teacher Academic data import completed!\n")

if __name__ == "__main__":
    main()
