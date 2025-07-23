from flask import Flask, request, jsonify
from flask_cors import CORS
from query_llm import CollegeQuerySystem

app = Flask(__name__)
CORS(app)  # Enable CORS

system = CollegeQuerySystem()

@app.route('/api/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    response = system.generate_response(data['query'])
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(port=5000, debug=True)