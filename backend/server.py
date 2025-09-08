from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import random

from query_llm import CollegeQuerySystem  # Your existing query system

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ------------------- Logging -------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('server.log'), logging.StreamHandler()]
)

# ------------------- Config -------------------
UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'md'}

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
@app.route('/api/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    response = CollegeQuerySystem().generate_response(query)
    query_logs.append({
        'id': len(query_logs) + 1,
        'query': query,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'response_time': '2.0s',
        'status': 'success',
        'response_length': len(response)
    })
    system_stats['total_queries'] += 1
    system_stats['successful_queries'] += 1
    return jsonify({'response': response})

@app.route('/admin/query', methods=['POST'])
def admin_query():
    return handle_query()

# ------------------- Main -------------------
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
