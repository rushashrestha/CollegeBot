from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from supabase import create_client, Client
from nepali_datetime import datetime as nepali_datetime
from datetime import datetime
import uuid
from dotenv import load_dotenv
import requests  

from query_llm import CollegeQuerySystem

# ------------------- PyTorch/CUDA Fix -------------------
import torch
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
torch.cuda.is_available = lambda: False
print("🔧 PyTorch configured to use CPU only")


# ------------------- Load Environment Variables -------------------
from dotenv import load_dotenv
load_dotenv()  # This loads the .env file

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ------------------- Debug Environment Variables -------------------
print("\n" + "="*60)
print("🔍 SUPABASE CONFIGURATION CHECK")
print("="*60)
print(f"📍 Supabase URL: {SUPABASE_URL[:50]}..." if SUPABASE_URL else "❌ MISSING SUPABASE_URL")
print(f"🔑 Anon Key: {'✅ Present' if SUPABASE_KEY else '❌ MISSING'} (Length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0})")
print(f"🔑 Service Key: {'✅ Present' if SUPABASE_SERVICE_KEY else '❌ MISSING'} (Length: {len(SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else 0})")

if SUPABASE_KEY:
    print(f"   Anon Key preview: {SUPABASE_KEY[:20]}...")
if SUPABASE_SERVICE_KEY:
    print(f"   Service Key preview: {SUPABASE_SERVICE_KEY[:20]}...")
print("="*60 + "\n")

# ------------------- Initialize Supabase Clients -------------------
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set in .env file!")

# Check if service key is available
if not SUPABASE_SERVICE_KEY:
    print("⚠️ WARNING: SUPABASE_SERVICE_ROLE_KEY not found in environment!")
    print("⚠️ Backend will use anon key - user creation will fail!")
    print("⚠️ Please add SUPABASE_SERVICE_ROLE_KEY to your .env file")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase_admin: Client = supabase
else:
    print("✅ Using Supabase Service Role Key for backend operations")
    # Use service_role key for ALL backend operations to bypass RLS and enable admin features
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    supabase_admin: Client = supabase
    print("✅ Supabase clients initialized successfully\n")

def test_service_key_permissions():
    """Test if current service key has admin permissions"""
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'apikey': SUPABASE_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"🔐 Service key test - Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Service key has admin permissions!")
            users = response.json()
            print(f"✅ Found {len(users)} users")
            return True
        else:
            print(f"❌ Service key test failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Service key test error: {e}")
        return False

app = Flask(__name__)
CORS(app, supports_credentials=True)

# ------------------- Config -------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
ALLOWED_EXTENSIONS = {'md'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"📁 Created data directory: {UPLOAD_FOLDER}")

print(f"📁 Using data directory: {UPLOAD_FOLDER}")
print(f"📁 Files in data directory: {os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else 'Directory not found'}")

# ------------------- CORS Configuration -------------------
@app.after_request
def after_request(response):
    # Only set headers if they're not already set (prevents duplicates)
    if 'Access-Control-Allow-Origin' not in response.headers:
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
    if 'Access-Control-Allow-Headers' not in response.headers:
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    if 'Access-Control-Allow-Methods' not in response.headers:
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    if 'Access-Control-Allow-Credentials' not in response.headers:
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Handle OPTIONS requests for all admin routes
@app.route('/admin/students/<student_id>', methods=['OPTIONS'])
@app.route('/admin/teachers/<teacher_id>', methods=['OPTIONS'])
@app.route('/admin/force-password-update/<user_id>', methods=['OPTIONS'])
@app.route('/admin/emergency-password-reset', methods=['OPTIONS'])
@app.route('/admin/delete-and-recreate-user', methods=['OPTIONS'])
def options_handler(student_id=None, teacher_id=None, user_id=None):
    return '', 200

# ------------------- Date Conversion Routes -------------------
@app.route('/convert/ad-to-bs', methods=['POST'])
def convert_ad_to_bs():
    try:
        data = request.get_json()
        ad_date_str = data.get('ad_date')
        
        if not ad_date_str:
            return jsonify({'error': 'AD date is required'}), 400
        
        ad_date = datetime.strptime(ad_date_str, '%Y-%m-%d')
        bs_date = nepali_datetime.from_datetime_date(ad_date.date())
        bs_date_str = bs_date.strftime('%Y-%m-%d')
        
        return jsonify({
            'ad_date': ad_date_str,
            'bs_date': bs_date_str
        })
        
    except Exception as e:
        logging.error(f"Error converting AD to BS: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/convert/bs-to-ad', methods=['POST'])
def convert_bs_to_ad():
    try:
        data = request.get_json()
        bs_date_str = data.get('bs_date')
        
        if not bs_date_str:
            return jsonify({'error': 'BS date is required'}), 400
        
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', bs_date_str):
            return jsonify({'error': 'BS date must be in YYYY-MM-DD format'}), 400
        
        try:
            bs_date = nepali_datetime.strptime(bs_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid BS date'}), 400
        
        ad_date = bs_date.to_datetime_date()
        ad_date_str = ad_date.strftime('%Y-%m-%d')
        
        return jsonify({
            'bs_date': bs_date_str,
            'ad_date': ad_date_str
        })
        
    except Exception as e:
        logging.error(f"Error converting BS to AD: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ------------------- Title Generation Function -------------------
def generate_chat_title(question):
    """Generate a meaningful title for chat sessions"""
    if not question or len(question.strip()) == 0:
        return "New Chat"
    
    question_lower = question.lower().strip()
    
    # Course-related queries
    if any(word in question_lower for word in ['course', 'subject', 'syllabus', 'curriculum']):
        if 'csit' in question_lower:
            return "CSIT Courses & Curriculum"
        elif 'bca' in question_lower:
            return "BCA Program Courses"
        elif 'bsw' in question_lower:
            return "BSW Course Structure"
        elif 'bbs' in question_lower:
            return "BBS Academic Courses"
        else:
            return "Course Information"
    
    # Person queries
    elif any(phrase in question_lower for phrase in ['who is', 'information about', 'tell me about', 'details about']):
        name_patterns = [
            r'(?:who is|information about|tell me about|details about)\s+([^?.!]*)',
            r'^(?:can you tell me about|i want to know about)\s+([^?.!]*)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, question_lower)
            if match and match.group(1).strip():
                name = match.group(1).strip().title()
                if len(name) > 2:
                    return f"About {name}"
        
        return "Personal Information"
    
    # Contact information
    elif any(word in question_lower for word in ['email', 'phone', 'contact', 'number']):
        if 'teacher' in question_lower or 'faculty' in question_lower:
            return "Faculty Contact Info"
        elif 'student' in question_lower:
            return "Student Contact Details"
        else:
            return "Contact Information"
    
    # Program information
    elif any(word in question_lower for word in ['program', 'degree', 'bachelor']):
        if 'csit' in question_lower:
            return "BSc CSIT Program Info"
        elif 'bca' in question_lower:
            return "BCA Degree Program"
        elif 'bsw' in question_lower:
            return "BSW Program Details"
        elif 'bbs' in question_lower:
            return "BBS Program Overview"
        else:
            return "Academic Programs"
    
    # Admission queries
    elif any(word in question_lower for word in ['admission', 'eligibility', 'fee', 'apply']):
        return "Admission Process & Fees"
    
    # Facility queries
    elif any(word in question_lower for word in ['facility', 'library', 'lab', 'campus']):
        return "College Facilities & Infrastructure"
    
    # Semester and academic queries
    elif any(word in question_lower for word in ['semester', 'credit', 'exam', 'assignment']):
        return "Academic Information"
    
    # Teacher/Faculty queries
    elif any(word in question_lower for word in ['teacher', 'faculty', 'professor', 'lecturer']):
        return "Faculty Information"
    
    # Student queries
    elif any(word in question_lower for word in ['student', 'batch', 'section', 'roll']):
        return "Student Information"
    
    else:
        stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'which', 'tell', 'me', 'about', 
                     'information', 'can', 'you', 'please', 'could', 'would', 'the', 'a', 'an', 'is'}
        
        words = [word for word in question.split() 
                if word.lower() not in stop_words and len(word) > 2]
        
        if words:
            meaningful_title = ' '.join(words[:4])
            meaningful_title = ' '.join(word.capitalize() for word in meaningful_title.split())
            return meaningful_title if len(meaningful_title) <= 40 else meaningful_title[:37] + '...'
        
        first_words = ' '.join(question.split()[:4])
        return first_words if len(first_words) <= 40 else first_words[:37] + '...'

# ------------------- Admin Routes -------------------

@app.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        print("📊 Fetching admin stats...")
        
        # Get student count
        try:
            all_students = supabase.table('students_data').select('id').execute()
            total_students = len(all_students.data) if all_students.data else 0
            print(f"👥 Total students: {total_students}")
        except Exception as e:
            print(f"⚠️ Error getting student count: {e}")
            total_students = 0

        # Get teacher count
        try:
            all_teachers = supabase.table('teachers_data').select('id').execute()
            total_teachers = len(all_teachers.data) if all_teachers.data else 0
            print(f"👨‍🏫 Total teachers: {total_teachers}")
        except Exception as e:
            print(f"⚠️ Error getting teacher count: {e}")
            total_teachers = 0

        # Get total queries from chat sessions
        try:
            all_sessions = supabase.table('chat_sessions').select('id').execute()
            total_queries = len(all_sessions.data) if all_sessions.data else 0
            print(f"💬 Total queries: {total_queries}")
        except Exception as e:
            print(f"⚠️ Error getting query count: {e}")
            total_queries = 0

        # Get active users (users with sessions in last 24 hours)
        try:
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            active_response = supabase.table('chat_sessions')\
                .select('user_email')\
                .gte('created_at', yesterday)\
                .execute()
            active_users = len(set([s['user_email'] for s in active_response.data])) if active_response.data else 0
        except Exception as e:
            print(f"⚠️ Error getting active users: {e}")
            active_users = 0

        # Get document count
        doc_count = 0
        if os.path.exists(UPLOAD_FOLDER):
            doc_count = len([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.md')])
        
        success_rate = 95.5

        return jsonify({
            'totalStudents': total_students,
            'totalTeachers': total_teachers,
            'totalQueries': total_queries,
            'activeUsers': active_users,
            'totalDocuments': doc_count,
            'successRate': success_rate,
            'systemUptime': '48.0h'
        })
    except Exception as e:
        logging.error(f"Error in /admin/stats: {str(e)}")
        return jsonify({
            'totalStudents': 0,
            'totalTeachers': 0,
            'totalQueries': 0,
            'activeUsers': 0,
            'totalDocuments': 0,
            'successRate': 0,
            'systemUptime': '0h',
            'error': str(e)
        }), 500

@app.route('/admin/queries', methods=['GET'])
def get_query_logs():
    try:
        sessions = supabase.table('chat_sessions')\
            .select('*, chat_messages(*)')\
            .order('created_at', desc=True)\
            .limit(50)\
            .execute()
        
        query_logs = []
        for session in sessions.data:
            if session.get('chat_messages'):
                for msg in session['chat_messages']:
                    if msg['sender'] == 'user':
                        query_logs.append({
                            'id': msg['id'],
                            'query': msg['message_text'][:100] + ('...' if len(msg['message_text']) > 100 else ''),
                            'timestamp': msg['created_at'],
                            'user_email': session.get('user_email', 'Unknown'),
                            'user_role': session.get('user_role', 'guest'),
                            'session_id': session['id'],
                            'status': 'success'
                        })
        
        return jsonify({'queries': query_logs[:20]})
    except Exception as e:
        logging.error(f"Error in /admin/queries: {str(e)}")
        return jsonify({'error': str(e), 'queries': []}), 500

@app.route('/admin/documents', methods=['GET'])
def get_documents():
    try:
        print("📄 Fetching documents...")
        docs = []
        
        if os.path.exists(UPLOAD_FOLDER):
            md_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.md')]
            print(f"📁 Found {len(md_files)} .md files: {md_files}")
            
            for i, filename in enumerate(md_files):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                try:
                    stat = os.stat(file_path)
                    file_size_kb = stat.st_size / 1024
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        chunks = content.count('\n\n') + 1
                    
                    docs.append({
                        'id': i + 1,
                        'name': filename,
                        'size': f"{file_size_kb:.1f}KB",
                        'status': 'active',
                        'chunks': chunks,
                        'lastModified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    print(f"✅ Added document: {filename} ({file_size_kb:.1f}KB, {chunks} chunks)")
                    
                except Exception as file_error:
                    print(f"❌ Error reading file {filename}: {file_error}")
                    docs.append({
                        'id': i + 1,
                        'name': filename,
                        'size': '0KB',
                        'status': 'error',
                        'chunks': 0,
                        'lastModified': 'Unknown'
                    })
        else:
            print(f"❌ Data directory not found: {UPLOAD_FOLDER}")
        
        print(f"📄 Returning {len(docs)} documents")
        return jsonify({'documents': docs})
        
    except Exception as e:
        print(f"❌ Error in /admin/documents: {str(e)}")
        return jsonify({'error': str(e), 'documents': []}), 500

@app.route('/admin/documents/upload', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and file.filename.endswith('.md'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            
            file.save(file_path)
            print(f"✅ Document uploaded: {filename} -> {file_path}")
            
            return jsonify({
                'success': True, 
                'filename': filename, 
                'message': f'Document {filename} uploaded successfully'
            })
        else:
            return jsonify({'error': 'Only .md files allowed'}), 400
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Document deleted: {safe_filename}")
            return jsonify({'success': True, 'message': f'Document {safe_filename} deleted'})
        else:
            print(f"❌ Document not found: {file_path}")
            return jsonify({'error': 'Document not found'}), 404
            
    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/documents/<filename>/reprocess', methods=['POST'])
def reprocess_document(filename):
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if os.path.exists(file_path):
            print(f"✅ Document reprocess triggered: {safe_filename}")
            return jsonify({'success': True, 'message': f'Document {safe_filename} reprocessing started'})
        else:
            return jsonify({'error': 'Document not found'}), 404
            
    except Exception as e:
        print(f"❌ Reprocess error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ------------------- Students CRUD -------------------
@app.route('/admin/students', methods=['GET'])
def get_students():
    try:
        response = supabase.table('students_data').select('*').order('name').execute()
        return jsonify({'students': response.data})
    except Exception as e:
        logging.error(f"Error fetching students: {str(e)}")
        return jsonify({'error': str(e), 'students': []}), 500

@app.route('/admin/students', methods=['POST'])
def add_student():
    try:
        data = request.get_json()
        print(f"📝 Adding student with data: {data}")
        
        required_fields = ['email', 'password', 'full_name', 'name', 'roll_no', 'program']
        for field in required_fields:
            if not data.get(field):
                print(f"❌ Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if email already exists in students table
        existing_student = supabase.table('students_data').select('*').eq('email', data['email']).execute()
        if existing_student.data:
            print(f"❌ Email already exists: {data['email']}")
            return jsonify({'error': 'Email already exists. Please use a different email address.'}), 400
        
        # Create user in Supabase Auth using DIRECT API (not SDK)
        try:
            auth_url = f"{SUPABASE_URL}/auth/v1/admin/users"
            headers = {
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'apikey': SUPABASE_KEY,
                'Content-Type': 'application/json'
            }
            
            auth_payload = {
                "email": data['email'],
                "password": data['password'],
                "email_confirm": True,
                "user_metadata": {
                    "role": "student",
                    "full_name": data['full_name']
                }
            }
            
            print(f"🔐 Creating auth user via direct API...")
            auth_response = requests.post(auth_url, json=auth_payload, headers=headers, timeout=30)
            
            print(f"🔐 Auth API Response Status: {auth_response.status_code}")
            print(f"🔐 Auth API Response: {auth_response.text}")
            
            if auth_response.status_code == 200:
                user_data = auth_response.json()
                supabase_user_id = user_data['id']
                print(f"✅ Supabase auth user created via direct API: {supabase_user_id}")
            else:
                error_detail = auth_response.text
                print(f"❌ Auth API failed: {error_detail}")
                raise Exception(f"Auth API returned {auth_response.status_code}: {error_detail}")
                
        except Exception as auth_error:
            print(f"❌ Auth user creation failed: {auth_error}")
            return jsonify({'error': f'Failed to create authentication: {str(auth_error)}'}), 500
        
        # Generate student_id
        student_id = f"{data['roll_no']}-{data['program']}".upper().replace(' ', '')
        existing_id = supabase.table('students_data').select('student_id').eq('student_id', student_id).execute()
        if existing_id.data:
            student_id = f"{student_id}-{str(uuid.uuid4())[:8]}"
        
        # Create student record
        student_data = {
            'student_id': student_id,
            'name': data['name'],
            'dob_ad': data.get('dob_ad'),
            'dob_bs': data.get('dob_bs'),
            'gender': data.get('gender'),
            'phone': data.get('phone'),
            'email': data['email'],
            'perm_address': data.get('perm_address'),
            'temp_address': data.get('temp_address'),
            'program': data['program'],
            'batch': data.get('batch'),
            'section': data.get('section'),
            'year_semester': data.get('year_semester'),
            'roll_no': data['roll_no'],
            'symbol_no': data.get('symbol_no'),
            'registration_no': data.get('registration_no'),
            'joined_date': data.get('joined_date'),
            'supabase_user_id': supabase_user_id
        }
        
        student_response = supabase.table('students_data').insert(student_data).execute()
        
        if student_response.data:
            print(f"✅ Student created successfully")
            return jsonify({
                'success': True,
                'message': 'Student added successfully! They can now login.',
                'student': student_response.data[0]
            })
        else:
            # Rollback: delete auth user if student creation fails
            try:
                delete_url = f"{SUPABASE_URL}/auth/v1/admin/users/{supabase_user_id}"
                requests.delete(delete_url, headers=headers)
                print(f"✅ Rollback: deleted auth user {supabase_user_id}")
            except Exception as delete_error:
                print(f"⚠️ Failed to delete auth user during rollback: {delete_error}")
            
            return jsonify({'error': 'Failed to create student record'}), 500
            
    except Exception as e:
        print(f"❌ Error adding student: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/students/<student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.get_json()
        print(f"🔄 Updating student {student_id}")
        
        allowed_fields = [
            'name', 'dob_ad', 'dob_bs', 'gender', 'phone', 'email',
            'perm_address', 'temp_address', 'program', 'batch', 'section',
            'year_semester', 'roll_no', 'symbol_no', 'registration_no', 'joined_date'
        ]
        
        update_data = {key: value for key, value in data.items() if key in allowed_fields}
        
        response = supabase.table('students_data')\
            .update(update_data)\
            .eq('id', student_id)\
            .execute()
        
        if response.data:
            # Update user metadata if full_name changed
            if data.get('full_name'):
                try:
                    student = response.data[0]
                    if student.get('supabase_user_id'):
                        supabase_admin.auth.admin.update_user_by_id(
                            student['supabase_user_id'],
                            {"user_metadata": {"full_name": data['full_name']}}
                        )
                except Exception as meta_error:
                    print(f"⚠️ Failed to update user metadata: {meta_error}")
            
            return jsonify({
                'success': True,
                'message': 'Student updated successfully',
                'student': response.data[0]
            })
        else:
            return jsonify({'error': 'Student not found'}), 404
            
    except Exception as e:
        logging.error(f"Error updating student: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        # Get student details
        student_response = supabase.table('students_data').select('*').eq('id', student_id).execute()
        if not student_response.data:
            return jsonify({'error': 'Student not found'}), 404
        
        student = student_response.data[0]
        supabase_user_id = student.get('supabase_user_id')
        
        # Delete from students_data
        supabase.table('students_data').delete().eq('id', student_id).execute()
        
        # Delete from Supabase Auth
        if supabase_user_id:
            try:
                supabase_admin.auth.admin.delete_user(supabase_user_id)
                print(f"✅ Deleted auth user: {supabase_user_id}")
            except Exception as auth_error:
                print(f"⚠️ Failed to delete auth user: {auth_error}")
        
        return jsonify({
            'success': True,
            'message': 'Student deleted successfully'
        })
    except Exception as e:
        print(f"❌ Error deleting student: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ------------------- Teachers CRUD -------------------
@app.route('/admin/teachers', methods=['GET'])
def get_teachers():
    try:
        response = supabase.table('teachers_data').select('*').order('name').execute()
        return jsonify({'teachers': response.data})
    except Exception as e:
        logging.error(f"Error fetching teachers: {str(e)}")
        return jsonify({'error': str(e), 'teachers': []}), 500

@app.route('/admin/teachers', methods=['POST'])
def add_teacher():
    try:
        data = request.get_json()
        print(f"📝 Adding teacher with data: {data}")
        
        required_fields = ['email', 'password', 'full_name', 'name', 'designation', 'subject']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if email already exists
        existing_teacher = supabase.table('teachers_data').select('*').eq('email', data['email']).execute()
        if existing_teacher.data:
            return jsonify({'error': 'Email already exists. Please use a different email address.'}), 400
        
        # Create user in Supabase Auth using DIRECT API
        try:
            auth_url = f"{SUPABASE_URL}/auth/v1/admin/users"
            headers = {
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'apikey': SUPABASE_KEY,
                'Content-Type': 'application/json'
            }
            
            auth_payload = {
                "email": data['email'],
                "password": data['password'],
                "email_confirm": True,
                "user_metadata": {
                    "role": "teacher",
                    "full_name": data['full_name']
                }
            }
            
            print(f"🔐 Creating teacher auth user via direct API...")
            auth_response = requests.post(auth_url, json=auth_payload, headers=headers, timeout=30)
            
            print(f"🔐 Auth API Response Status: {auth_response.status_code}")
            print(f"🔐 Auth API Response: {auth_response.text}")
            
            if auth_response.status_code == 200:
                user_data = auth_response.json()
                supabase_user_id = user_data['id']
                print(f"✅ Supabase auth teacher created via direct API: {supabase_user_id}")
            else:
                error_detail = auth_response.text
                print(f"❌ Auth API failed: {error_detail}")
                raise Exception(f"Auth API returned {auth_response.status_code}: {error_detail}")
                
        except Exception as auth_error:
            print(f"❌ Auth user creation failed: {auth_error}")
            return jsonify({'error': f'Failed to create authentication: {str(auth_error)}'}), 500
        
        # Create teacher record
        teacher_data = {
            'name': data['name'],
            'designation': data['designation'],
            'phone': data.get('phone'),
            'email': data['email'],
            'address': data.get('address'),
            'degree': data.get('degree'),
            'subject': data['subject'],
            'supabase_user_id': supabase_user_id
        }
        
        teacher_response = supabase.table('teachers_data').insert(teacher_data).execute()
        
        if teacher_response.data:
            print(f"✅ Teacher created successfully")
            return jsonify({
                'success': True,
                'message': 'Teacher added successfully! They can now login.',
                'teacher': teacher_response.data[0]
            })
        else:
            # Rollback: delete auth user if teacher creation fails
            try:
                delete_url = f"{SUPABASE_URL}/auth/v1/admin/users/{supabase_user_id}"
                headers = {
                    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                    'apikey': SUPABASE_KEY
                }
                requests.delete(delete_url, headers=headers)
                print(f"✅ Rollback: deleted auth user {supabase_user_id}")
            except Exception as delete_error:
                print(f"⚠️ Failed to delete auth user during rollback: {delete_error}")
            
            return jsonify({'error': 'Failed to create teacher record'}), 500
            
    except Exception as e:
        print(f"❌ Error adding teacher: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/teachers/<teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    try:
        data = request.get_json()
        print(f"🔄 Updating teacher {teacher_id}")
        
        allowed_fields = [
            'name', 'designation', 'phone', 'email', 'address', 'degree', 'subject'
        ]
        
        update_data = {key: value for key, value in data.items() if key in allowed_fields}
        
        response = supabase.table('teachers_data')\
            .update(update_data)\
            .eq('id', teacher_id)\
            .execute()
        
        if response.data:
            # Update user metadata if full_name changed
            if data.get('full_name'):
                try:
                    teacher = response.data[0]
                    if teacher.get('supabase_user_id'):
                        supabase_admin.auth.admin.update_user_by_id(
                            teacher['supabase_user_id'],
                            {"user_metadata": {"full_name": data['full_name']}}
                        )
                except Exception as meta_error:
                    print(f"⚠️ Failed to update user metadata: {meta_error}")
            
            return jsonify({
                'success': True,
                'message': 'Teacher updated successfully',
                'teacher': response.data[0]
            })
        else:
            return jsonify({'error': 'Teacher not found'}), 404
            
    except Exception as e:
        logging.error(f"Error updating teacher: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/teachers/<teacher_id>', methods=['DELETE'])
def delete_teacher(teacher_id):
    try:
        # Get teacher details
        teacher_response = supabase.table('teachers_data').select('*').eq('id', teacher_id).execute()
        if not teacher_response.data:
            return jsonify({'error': 'Teacher not found'}), 404
        
        teacher = teacher_response.data[0]
        supabase_user_id = teacher.get('supabase_user_id')
        
        # Delete from teachers_data
        supabase.table('teachers_data').delete().eq('id', teacher_id).execute()
        
        # Delete from Supabase Auth
        if supabase_user_id:
            try:
                supabase_admin.auth.admin.delete_user(supabase_user_id)
                print(f"✅ Deleted auth user: {supabase_user_id}")
            except Exception as auth_error:
                print(f"⚠️ Failed to delete auth user: {auth_error}")
        
        return jsonify({
            'success': True,
            'message': 'Teacher deleted successfully'
        })
    except Exception as e:
        print(f"❌ Error deleting teacher: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-password-changed', methods=['POST'])
def mark_password_changed():
    """Mark that user has changed their password"""
    try:
        data = request.get_json()
        email = data.get('email')
        table = data.get('table')
        
        if not email or not table:
            return jsonify({'error': 'Email and table required'}), 400
        
        # Update the password_changed flag
        response = supabase.table(table)\
            .update({'password_changed': True})\
            .eq('email', email)\
            .execute()
        
        if response.data:
            print(f"✅ Password change marked for {email} in {table}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logging.error(f"Error marking password changed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-password-changed', methods=['POST'])
def check_password_changed():
    """Check if user has changed their password"""
    try:
        data = request.get_json()
        email = data.get('email')
        table = data.get('table')
        
        if not email or not table:
            return jsonify({'error': 'Email and table required'}), 400
        
        # Check the password_changed flag
        response = supabase.table(table)\
            .select('password_changed')\
            .eq('email', email)\
            .execute()
        
        if response.data and len(response.data) > 0:
            password_changed = response.data[0].get('password_changed', False)
            return jsonify({'password_changed': password_changed})
        else:
            return jsonify({'password_changed': False})
            
    except Exception as e:
        logging.error(f"Error checking password changed: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/admin/force-password-update/<user_id>', methods=['POST'])
def force_password_update(user_id):
    """Force update password by user ID"""
    try:
        data = request.get_json()
        new_password = data.get('password', 'student123')
        
        print(f"🔐 Force updating password for user ID: {user_id}")
        
        update_url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/json'
        }
        
        update_payload = {
            "password": new_password
        }
        
        response = requests.put(
            update_url,
            json=update_payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': f'Password updated to: {new_password}'
            })
        else:
            return jsonify({
                'error': response.text,
                'status': response.status_code
            }), response.status_code
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ------------------- Analytics Endpoint -------------------
@app.route('/admin/analytics', methods=['GET'])
def get_analytics():
    try:
        from datetime import datetime, timedelta
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        sessions = supabase.table('chat_sessions')\
            .select('created_at')\
            .gte('created_at', seven_days_ago)\
            .execute()
        
        daily_counts = {}
        for session in sessions.data:
            date = session['created_at'][:10]
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        chart_data = [
            {'date': date, 'queries': count}
            for date, count in sorted(daily_counts.items())
        ]
        
        return jsonify({
            'weeklyTrend': chart_data,
            'totalThisWeek': sum(daily_counts.values())
        })
    except Exception as e:
        logging.error(f"Error fetching analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ------------------- LLM Query Route -------------------
@app.route('/api/query', methods=['POST'])
def handle_query():
    try:
        data = request.get_json()
        query = data.get('query', '')
        user_role = data.get('user_role', 'guest')
        user_data = data.get('user_data', None)
        session_id = data.get('session_id', None)
        is_guest = data.get('is_guest', True)
        
        print(f"🔍 Received query:")
        print(f"   - Role: {user_role}")
        print(f"   - Query: '{query}'")
        print(f"   - Session ID: {session_id}")
        print(f"   - Is Guest: {is_guest}")

        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Initialize query system
        system = CollegeQuerySystem()
        
        print(f"🔄 Calling LLM with user_role: {user_role}")
        response = system.generate_response(query, user_role, user_data)
        
        # Generate suggested title
        suggested_title = generate_chat_title(query)

        # Set access_restricted based on response content
        access_restricted = any(phrase in response.lower() for phrase in [
            'guest users can only access',
            'please log in', 
            'students can only access',
            'access restricted'
        ])

        print(f"📋 Response generated:")
        print(f"   - Length: {len(response)} chars")
        print(f"   - Access Restricted: {access_restricted}")
        print(f"   - Suggested Title: {suggested_title}")
        
        return jsonify({
            'response': response,
            'access_restricted': access_restricted,
            'user_role': user_role,
            'suggested_title': suggested_title,
            'session_id': session_id,
            'is_guest': is_guest
        })
        
    except Exception as e:
        logging.error(f"❌ Error in /api/query: {str(e)}")
        print(f"💥 Error processing query: {str(e)}")
        
        return jsonify({
            'error': str(e),
            'response': f"Sorry, I encountered an error: {str(e)}. Please try again.",
            'access_restricted': False
        }), 500

# ------------------- User Data Route -------------------
@app.route('/api/user-data', methods=['POST'])
def get_user_data():
    try:
        data = request.get_json()
        email = data.get('email')
        table = data.get('table')
        
        if not email or not table:
            return jsonify({'error': 'Email and table required'}), 400
        
        system = CollegeQuerySystem()
        user_data = system._query_supabase(table, params={"email": f"eq.{email}"})
        
        if user_data:
            return jsonify({'user_data': user_data[0]})
        else:
            return jsonify({'user_data': None})
            
    except Exception as e:
        logging.error("Error fetching user data: %s", str(e))
        return jsonify({'error': str(e)}), 500


# ------------------- Health Check -------------------
@app.route('/health', methods=['GET'])
def health_check():
    global system_stats
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'total_queries': system_stats['total_queries'],
        'successful_queries': system_stats['successful_queries'],
        'uptime_hours': (datetime.now() - system_stats['start_time']).total_seconds() / 3600
    })

# ------------------- Main -------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    print("🚀 Flask server starting on http://127.0.0.1:5000")
    print("📝 Using Supabase Auth for authentication")
    print("🔓 Only highly sensitive security information is restricted")
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)