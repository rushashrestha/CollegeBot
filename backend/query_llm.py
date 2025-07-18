import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

class CollegeQuerySystem:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectordb_path = "db"
        
        # Program information
        self.programs = {
            "csit": {
                "name": "Bachelor of Science in Computer Science and IT",
                "duration": "4 years (8 semesters)",
                "keywords": ["csit", "computer science"]
            },
            "bca": {
                "name": "Bachelor of Computer Applications",
                "duration": "4 years (8 semesters)",
                "keywords": ["bca", "computer applications"]
            },
            "bsw": {
                "name": "Bachelor of Social Work",
                "duration": "4 years (8 semesters)",
                "keywords": ["bsw", "social work"]
            },
            "bbs": {
                "name": "Bachelor of Business Studies",
                "duration": "4 years (8 semesters)",
                "keywords": ["bbs", "business studies"]
            }
        }

    def get_vectordb(self):
        """Load the vector database"""
        return Chroma(
            persist_directory=self.vectordb_path,
            embedding_function=self.embedding
        )

    def detect_program(self, question):
        """Identify which program the question is about"""
        question_lower = question.lower()
        for program, data in self.programs.items():
            if any(kw in question_lower for kw in data["keywords"]):
                return program, data
        return None, None

    def query_documents(self, question, program=None, k=10):
        """Query documents with optional program filter"""
        vectordb = self.get_vectordb()
        if program:
            docs = vectordb.similarity_search(
                question,
                k=k,
                filter={"program": program}
            )
        else:
            docs = vectordb.similarity_search(question, k=k)
        return "\n\n".join([doc.page_content for doc in docs])

    def _extract_courses_directly(self, context, semester):
        """Directly extract courses from table data"""
        courses = []
        current_semester = False
        
        for line in context.split('\n'):
            if f"Semester {semester}" in line or f"| Semester {semester}" in line:
                current_semester = True
                continue
            elif "Semester" in line and current_semester:
                break
                
            if current_semester and '|' in line and 'Course Code' not in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 3:
                    course_code = parts[1] if len(parts) > 1 else ""
                    course_name = parts[2] if len(parts) > 2 else ""
                    credits = parts[3] if len(parts) > 3 else ""
                    courses.append(f"- {course_name} ({course_code}): {credits} credits")
        
        return courses

    def _handle_course_listing(self, question, program_data):
        """Strict course listing handler that only uses source data"""
        # First try to get direct table data
        context = self.query_documents(
            f"Semester courses from {program_data['name']}",
            program=program_data['keywords'][0],
            k=15  # Get more documents to ensure we capture full tables
        )
        
        # Extract semester number from question
        semester = next((word for word in question.split() if word.isdigit()), "1")
        
        # Direct extraction from tables
        courses = self._extract_courses_directly(context, semester)
        
        if courses:
            return (
                f"{program_data['name']} Semester {semester} Courses:\n" +
                '\n'.join(courses) +
                f"\n(Source: {program_data['keywords'][0].upper()} document)"
            )
        
        # Fallback to LLM with strict instructions if direct extraction fails
        prompt = ChatPromptTemplate.from_template("""
        EXTRACT DON'T CREATE! List courses EXACTLY as shown in this context:
        {context}
        
        For Semester {semester} of {program}.
        
        Rules:
        1. Use ONLY the course names and codes from tables
        2. NEVER invent new courses
        3. Format as:
        - Course Name (CODE): Credits
        - ...
        
        4. If no courses found, say "Course information not available"
        """)
        
        chain = prompt | ChatGroq(
            temperature=0,  # Minimize creativity
            model_name="llama3-70b-8192",
            groq_api_key=os.getenv("GROQ_API_KEY")
        ) | StrOutputParser()
        
        return chain.invoke({
            "program": program_data['name'],
            "semester": semester,
            "context": context
        }) + f"\n(Source: {program_data['keywords'][0].upper()} document)"

    def generate_response(self, question):
        """Generate response with strict adherence to source data"""
        program, program_data = self.detect_program(question)
        
        # Handle semester count questions
        if "how many semesters" in question.lower() and program_data:
            return f"{program_data['name']} has {program_data['duration']}.\n(Source: {program.upper()} document)"
        
        # Handle course listing questions
        if any(phrase in question.lower() for phrase in 
              ["courses in semester", "list of courses", "course structure", "subjects in"]):
            if not program_data:
                return "Please specify which program (e.g., BCA, CSIT)."
            return self._handle_course_listing(question, program_data)
        
        # General questions
        context = self.query_documents(question, program)
        
        prompt = ChatPromptTemplate.from_template("""
        Answer this question using ONLY this context:
        {context}
        
        Question: {question}
        
        Rules:
        1. Be factual and concise
        2. Never invent information
        3. If unsure, say "Information not available in documents"
        4. Add "(Source: {source})" at the end
        """)
        
        chain = prompt | ChatGroq(
            temperature=0.1,  # Low temperature for accuracy
            model_name="llama3-70b-8192",
            groq_api_key=os.getenv("GROQ_API_KEY")
        ) | StrOutputParser()
        
        return chain.invoke({
            "question": question,
            "context": context,
            "source": program.upper() + " document" if program else "college documents"
        })

def interactive_chat():
    print("\nCollege Program Information System")
    print("Supports: BCA, CSIT, BSW, BBS")
    print("Type 'exit' to quit\n")
    
    system = CollegeQuerySystem()
    
    while True:
        try:
            question = input("\nYour question: ").strip()
            if question.lower() in ['exit', 'quit']:
                break
                
            response = system.generate_response(question)
            print(f"\n{response}\n")
        except Exception as e:
            print(f"\nError: {str(e)}\n")

if __name__ == "__main__":
    interactive_chat()