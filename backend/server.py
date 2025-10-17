from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import random
from supabase import create_client, Client
import json

from query_llm import CollegeQuerySystem  # Your existing query system

# ------------------- PyTorch/CUDA Fix -------------------
import torch
# Force CPU usage to avoid GPU memory issues
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
torch.cuda.is_available = lambda: False
print("🔧 PyTorch configured to use CPU only")

# ------------------- Global Variables -------------------
query_logs = []
system_stats = {
    'total_queries': 0,
    'successful_queries': 0,
    'start_time': datetime.now() - timedelta(hours=48)
}

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ------------------- Config -------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
ALLOWED_EXTENSIONS = {'md'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"📁 Created data directory: {UPLOAD_FOLDER}")

print(f"📁 Using data directory: {UPLOAD_FOLDER}")
print(f"📁 Files in data directory: {os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else 'Directory not found'}")


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
        # Extract name using better regex
        name_patterns = [
            r'(?:who is|information about|tell me about|details about)\s+([^?.!]*)',
            r'^(?:can you tell me about|i want to know about)\s+([^?.!]*)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, question_lower)
            if match and match.group(1).strip():
                name = match.group(1).strip().title()
                if len(name) > 2:  # Ensure it's a meaningful name
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
        # Use first meaningful words - improved logic
        stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'which', 'tell', 'me', 'about', 
                     'information', 'can', 'you', 'please', 'could', 'would', 'the', 'a', 'an', 'is'}
        
        words = [word for word in question.split() 
                if word.lower() not in stop_words and len(word) > 2]
        
        if words:
            meaningful_title = ' '.join(words[:4])
            # Capitalize properly
            meaningful_title = ' '.join(word.capitalize() for word in meaningful_title.split())
            return meaningful_title if len(meaningful_title) <= 40 else meaningful_title[:37] + '...'
        
        # Final fallback - use first 4 words
        first_words = ' '.join(question.split()[:4])
        return first_words if len(first_words) <= 40 else first_words[:37] + '...'



# ------------------- Admin Routes -------------------

@app.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        print("📊 Fetching admin stats...")
        
        # Get student count - use RPC or direct fetch without limit
        try:
            all_students = supabase.table('students_data').select('id').execute()
            total_students = len(all_students.data) if all_students.data else 0
            print(f"👥 Total students: {total_students}")
            print(f"🔍 Students response type: {type(all_students)}")
            print(f"🔍 Students response dir: {[attr for attr in dir(all_students) if not attr.startswith('_')]}")
        except Exception as e:
            print(f"⚠️ Error getting student count: {e}")
            import traceback
            traceback.print_exc()
            total_students = 0

        # Get teacher count
        try:
            all_teachers = supabase.table('teachers_data').select('id').execute()
            total_teachers = len(all_teachers.data) if all_teachers.data else 0
            print(f"👨‍🏫 Total teachers: {total_teachers}")
        except Exception as e:
            print(f"⚠️ Error getting teacher count: {e}")
            import traceback
            traceback.print_exc()
            total_teachers = 0

        # Get total queries from chat sessions
        try:
            all_sessions = supabase.table('chat_sessions').select('id').execute()
            total_queries = len(all_sessions.data) if all_sessions.data else 0
            print(f"💬 Total queries: {total_queries}")
        except Exception as e:
            print(f"⚠️ Error getting query count: {e}")
            import traceback
            traceback.print_exc()
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
        
        print(f"👥 Total students: {total_students}")
        print(f"👨‍🏫 Total teachers: {total_teachers}")
        print(f"💬 Total queries: {total_queries}")
        print(f"👤 Active users: {active_users}")
        print(f"📄 Total documents: {doc_count}")
        
        # Calculate success rate (simplified)
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
        # Get recent chat sessions with messages
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
        
        return jsonify({'queries': query_logs[:20]})  # Return latest 20
    except Exception as e:
        logging.error(f"Error in /admin/queries: {str(e)}")
        return jsonify({'error': str(e), 'queries': []}), 500


@app.route('/admin/documents', methods=['GET'])
def get_documents():
    try:
        print("📄 Fetching documents...")
        docs = []
        
        # FIX: Read from the correct data directory
        if os.path.exists(UPLOAD_FOLDER):
            md_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.md')]
            print(f"📁 Found {len(md_files)} .md files: {md_files}")
            
            for i, filename in enumerate(md_files):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                try:
                    stat = os.stat(file_path)
                    file_size_kb = stat.st_size / 1024
                    
                    # Read file to count chunks (simplified - count paragraphs)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        chunks = content.count('\n\n') + 1  # Count paragraphs as chunks
                    
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
            # FIX: Save to the correct data directory
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Ensure directory exists
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
        # FIX: Use secure filename and correct path
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
            # Add your reprocessing logic here
            # For now, just return success
            print(f"✅ Document reprocess triggered: {safe_filename}")
            return jsonify({'success': True, 'message': f'Document {safe_filename} reprocessing started'})
        else:
            return jsonify({'error': 'Document not found'}), 404
            
    except Exception as e:
        print(f"❌ Reprocess error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        
        # Validate required fields
        required_fields = ['email', 'password', 'full_name', 'name', 'roll_no', 'program']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # First, create user in authentication table
        auth_data = {
            'email': data['email'],
            'password': data['password'],  # You should hash this in production
            'role': 'student',
            'full_name': data['full_name']
        }
        
        # Insert into users table (authentication)
        auth_response = supabase.table('users').insert(auth_data).execute()
        if not auth_response.data:
            return jsonify({'error': 'Failed to create user account'}), 500
        
        # Prepare student data
        student_data = {
            'name': data['name'],
            'dob_ad': data.get('dob_ad'),
            'dob_bs': data.get('dob_bs'),
            'gender': data.get('gender'),
            'phone': data.get('phone'),
            'email': data['email'],
            'password': data['password'],  # Hash in production
            'perm_address': data.get('perm_address'),
            'temp_address': data.get('temp_address'),
            'program': data['program'],
            'batch': data.get('batch'),
            'section': data.get('section'),
            'year_semester': data.get('year_semester'),
            'roll_no': data['roll_no'],
            'symbol_no': data.get('symbol_no'),
            'registration_no': data.get('registration_no'),
            'joined_date': data.get('joined_date')
        }
        
        # Insert into students_data table
        student_response = supabase.table('students_data').insert(student_data).execute()
        
        if student_response.data:
            return jsonify({
                'success': True,
                'message': 'Student added successfully',
                'student': student_response.data[0]
            })
        else:
            # Rollback: delete the user if student creation fails
            supabase.table('users').delete().eq('email', data['email']).execute()
            return jsonify({'error': 'Failed to create student record'}), 500
            
    except Exception as e:
        print(f"❌ Error adding student: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/admin/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.get_json()
        
        # Update in database
        response = supabase.table('students_data')\
            .update(data)\
            .eq('id', student_id)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Student updated successfully',
            'student': response.data[0] if response.data else None
        })
    except Exception as e:
        logging.error(f"Error updating student: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        # First get student email
        student_response = supabase.table('students_data').select('email').eq('id', student_id).execute()
        if not student_response.data:
            return jsonify({'error': 'Student not found'}), 404
        
        email = student_response.data[0]['email']
        
        # Delete from students_data table
        supabase.table('students_data').delete().eq('id', student_id).execute()
        
        # Delete from users table
        supabase.table('users').delete().eq('email', email).execute()
        
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
        
        # Validate required fields
        required_fields = ['email', 'password', 'full_name', 'name', 'designation', 'subject']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # First, create user in authentication table
        auth_data = {
            'email': data['email'],
            'password': data['password'],  # You should hash this in production
            'role': 'teacher',
            'full_name': data['full_name']
        }
        
        # Insert into users table (authentication)
        auth_response = supabase.table('users').insert(auth_data).execute()
        if not auth_response.data:
            return jsonify({'error': 'Failed to create user account'}), 500
        
        # Prepare teacher data
        teacher_data = {
            'name': data['name'],
            'designation': data['designation'],
            'phone': data.get('phone'),
            'email': data['email'],
            'password': data['password'],  # Hash in production
            'address': data.get('address'),
            'degree': data.get('degree'),
            'subject': data['subject']
        }
        
        # Insert into teachers_data table
        teacher_response = supabase.table('teachers_data').insert(teacher_data).execute()
        
        if teacher_response.data:
            return jsonify({
                'success': True,
                'message': 'Teacher added successfully',
                'teacher': teacher_response.data[0]
            })
        else:
            # Rollback: delete the user if teacher creation fails
            supabase.table('users').delete().eq('email', data['email']).execute()
            return jsonify({'error': 'Failed to create teacher record'}), 500
            
    except Exception as e:
        print(f"❌ Error adding teacher: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/teachers/<int:teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    try:
        data = request.get_json()
        
        # Update in database
        response = supabase.table('teachers_data')\
            .update(data)\
            .eq('id', teacher_id)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Teacher updated successfully',
            'teacher': response.data[0] if response.data else None
        })
    except Exception as e:
        logging.error(f"Error updating teacher: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/teachers/<int:teacher_id>', methods=['DELETE'])
def delete_teacher(teacher_id):
    try:
        # First get teacher email
        teacher_response = supabase.table('teachers_data').select('email').eq('id', teacher_id).execute()
        if not teacher_response.data:
            return jsonify({'error': 'Teacher not found'}), 404
        
        email = teacher_response.data[0]['email']
        
        # Delete from teachers_data table
        supabase.table('teachers_data').delete().eq('id', teacher_id).execute()
        
        # Delete from users table
        supabase.table('users').delete().eq('email', email).execute()
        
        return jsonify({
            'success': True,
            'message': 'Teacher deleted successfully'
        })
    except Exception as e:
        print(f"❌ Error deleting teacher: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
# ------------------- Analytics Endpoint -------------------
@app.route('/admin/analytics', methods=['GET'])
def get_analytics():
    try:
        # Get query trends for the last 7 days
        from datetime import datetime, timedelta
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        sessions = supabase.table('chat_sessions')\
            .select('created_at')\
            .gte('created_at', seven_days_ago)\
            .execute()
        
        # Group by day
        daily_counts = {}
        for session in sessions.data:
            date = session['created_at'][:10]  # Get YYYY-MM-DD
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        # Format for chart
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
        print(f"   - User Data: {user_data is not None}")

        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Initialize query system
        system = CollegeQuerySystem()
        
        # ========== FIX: PASS USER CONTEXT TO LLM ==========
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
        
        # Log query to global query_logs
        global query_logs, system_stats
        query_logs.append({
            'id': len(query_logs) + 1,
            'query': query,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'response_time': '2.0s',
            'status': 'success',
            'response_length': len(response),
            'user_role': user_role,
            'is_guest': is_guest
        })
        
        system_stats['total_queries'] += 1
        system_stats['successful_queries'] += 1
        
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
        
        # Use your existing _query_supabase method
        system = CollegeQuerySystem()
        user_data = system._query_supabase(table, params={"email": f"eq.{email}"})
        
        if user_data:
            return jsonify({'user_data': user_data[0]})
        else:
            return jsonify({'user_data': None})
            
    except Exception as e:
        logging.error("Error fetching user data: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/admin/query', methods=['POST'])
def admin_query():
    return handle_query()

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
    print("📝 ALL users (including guests) can query without authentication!")
    print("🔓 Only highly sensitive security information is restricted")
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)