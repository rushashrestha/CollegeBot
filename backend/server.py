from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import random

from query_llm import CollegeQuerySystem  # Your existing query system

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ------------------- Config -------------------
UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'md'}

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


# ------------------- Dummy Data -------------------
query_logs = [
    {'id': 1, 'query': 'What courses are available?', 'timestamp': '2025-01-08 10:30:15',
     'response_time': '2.3s', 'status': 'success', 'response_length': 256}
]

system_stats = {'total_queries': 15, 'successful_queries': 12, 'start_time': datetime.now() - timedelta(hours=48)}

students = [
    {'id': 1, 'name': 'Ramesh', 'email': 'ramesh@example.com', 'roll': 'BCA101'}
]

teachers = [
    {'id': 1, 'name': 'Mr. Sharma', 'email': 'sharma@example.com', 'department': 'CSIT'}
]

# ------------------- Admin Routes -------------------

@app.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        uptime = datetime.now() - system_stats['start_time']
        uptime_hours = uptime.total_seconds() / 3600
        total = system_stats['total_queries']
        success_rate = (system_stats['successful_queries'] / total * 100) if total else 100
        doc_count = len([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.md')]) if os.path.exists(UPLOAD_FOLDER) else 0

        return jsonify({
            'totalQueries': total,
            'successRate': round(success_rate, 1),
            'totalDocuments': doc_count,
            'activeUsers': random.randint(1, 5),
            'totalStudents': len(students),
            'totalTeachers': len(teachers),
            'systemUptime': f"{uptime_hours:.1f}h"
        })
    except Exception as e:
        logging.error("Error in /admin/stats: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/admin/queries', methods=['GET'])
def get_query_logs():
    return jsonify({'queries': list(reversed(query_logs[-20:]))})

@app.route('/admin/documents', methods=['GET'])
def get_documents():
    docs = []
    if os.path.exists(UPLOAD_FOLDER):
        for i, f in enumerate(os.listdir(UPLOAD_FOLDER)):
            if f.endswith('.md'):
                stat = os.stat(os.path.join(UPLOAD_FOLDER, f))
                docs.append({
                    'id': i + 1,
                    'name': f,
                    'size': f"{stat.st_size / 1024:.1f}KB",
                    'status': 'active',
                    'chunks': random.randint(1, 5),
                    'lastModified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return jsonify({'documents': docs})

@app.route('/admin/documents/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file.filename.endswith('.md'):
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return jsonify({'success': True, 'filename': filename, 'message': f'Document {filename} uploaded successfully'})
    return jsonify({'error': 'Only .md files allowed'}), 400

@app.route('/admin/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({'success': True, 'message': f'Document {filename} deleted'})
    return jsonify({'error': 'Document not found'}), 404

@app.route('/admin/students', methods=['GET'])
def get_students():
    return jsonify({'students': students})

@app.route('/admin/students', methods=['POST'])
def add_student():
    data = request.get_json()
    new_student = {'id': len(students) + 1, 'name': data['name'], 'email': data['email'], 'roll': data['roll']}
    students.append(new_student)
    return jsonify(new_student)

@app.route('/admin/teachers', methods=['GET'])
def get_teachers():
    return jsonify({'teachers': teachers})

@app.route('/admin/teachers', methods=['POST'])
def add_teacher():
    data = request.get_json()
    new_teacher = {'id': len(teachers) + 1, 'name': data['name'], 'email': data['email'], 'department': data['department']}
    teachers.append(new_teacher)
    return jsonify(new_teacher)

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
        
        # Log query
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
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'total_queries': system_stats['total_queries']
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