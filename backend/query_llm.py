import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
print(f"API Key loaded: {os.getenv('GROQ_API_KEY')[:10]}...")  # Shows first 10 chars

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
                "seats": 48,
                "keywords": ["csit", "computer science", "bsc csit"]
            },
            "bca": {
                "name": "Bachelor of Computer Applications",
                "duration": "4 years (8 semesters)",
                "seats": 38,
                "keywords": ["bca", "computer applications"]
            },
            "bsw": {
                "name": "Bachelor of Social Work",
                "duration": "4 years ",
                "seats": 60,
                "keywords": ["bsw", "social work"]
            },
            "bbs": {
                "name": "Bachelor of Business Studies",
                "duration": "4 years ",
                "seats": 60,
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

    def _clean_table_formatting(self, text):
        """Convert table data to more readable format"""
        lines = []
        for line in text.split('\n'):
            if '|' in line:
                # Simple table to list conversion
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 3 and not any(h in line.lower() for h in ['header', '---']):
                    lines.append(f"• {parts[2]} (Code: {parts[1]})")  # More user-friendly format
                continue
            lines.append(line)
        return '\n'.join(lines)

    def query_documents(self, question, program=None, k=15):
        """Enhanced document querying with multiple search strategies"""
        vectordb = self.get_vectordb()
        
        # Strategy 1: Direct search with program filter
        if program:
            try:
                docs = vectordb.similarity_search(
                    question,
                    k=k,
                    filter={"program": program}
                )
                if docs:
                    raw_context = "\n\n".join([doc.page_content for doc in docs])
                    return self._clean_table_formatting(raw_context)
            except:
                pass
        
        # Strategy 2: Broad search without filter
        docs = vectordb.similarity_search(question, k=k)
        if docs:
            raw_context = "\n\n".join([doc.page_content for doc in docs])
            return self._clean_table_formatting(raw_context)
        
        # Strategy 3: Keyword-based search for general college info
        general_terms = ["samriddhi", "college", "principal", "director", "chairman"]
        for term in general_terms:
            if term in question.lower():
                docs = vectordb.similarity_search(term, k=k)
                if docs:
                    raw_context = "\n\n".join([doc.page_content for doc in docs])
                    return self._clean_table_formatting(raw_context)
        
        return ""

    def _extract_courses_directly(self, context, semester):
        """Directly extract courses from table data and reformat"""
        courses = []
        current_semester = False
        
        for line in context.split('\n'):
            semester_patterns = [
                f"Semester {semester}",
                f"| Semester {semester}",
                f"## Semester {semester}",
                f"# Semester {semester}"
            ]
            
            if any(pattern in line for pattern in semester_patterns):
                current_semester = True
                continue
            elif any(f"Semester {i}" in line for i in range(1, 9) if i != int(semester)) and current_semester:
                break
                
            if current_semester and '|' in line and 'Course Code' not in line and line.strip():
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 3:
                    course_code = parts[1] if len(parts) > 1 else ""
                    course_name = parts[2] if len(parts) > 2 else ""
                    credits = parts[3] if len(parts) > 3 else ""
                    if course_name and course_name != "---":
                        courses.append(f"• {course_name} (Code: {course_code}, Credits: {credits})")
        
        return courses
    
    def _handle_course_listing(self, question, program_data):
        """Enhanced course listing handler"""
        # Get comprehensive context
        context = self.query_documents(
            f"courses curriculum syllabus {program_data['name']} semester",
            program=program_data['keywords'][0],
            k=20
        )
        
        # Extract semester number
        semester = "1"  # default
        words = question.split()
        for i, word in enumerate(words):
            if word.isdigit() and 1 <= int(word) <= 8:
                semester = word
                break
            elif word.lower() in ["first", "1st"]:
                semester = "1"
            elif word.lower() in ["second", "2nd"]:
                semester = "2"
            elif word.lower() in ["third", "3rd"]:
                semester = "3"
            elif word.lower() in ["fourth", "4th", "forth"]:
                semester = "4"
        
        # Try direct extraction first
        courses = self._extract_courses_directly(context, semester)
        
        if courses:
            return (
                f"{program_data['name']} Semester {semester} Courses:\n" +
                '\n'.join(courses) +
                f"\n\n(Source: {program_data['keywords'][0].upper()} curriculum document)"
            )
        
        # Fallback to LLM with enhanced prompt
        prompt = ChatPromptTemplate.from_template("""
        You are a helpful assistant that extracts course information from college documents.

        Context from college documents:
        {context}

        Question: {question}

        Instructions:
        1. Extract course information from any tables or text
        2. Present the information in a clear, bullet-point list format
        3. Include course names, codes, and credit hours when available
        4. Do NOT maintain the original table format
        5. Make the response easy to read

        Provide the course information as a well-formatted list:
        """)
        
        chain = prompt | ChatGroq(
            temperature=0.2,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        ) | StrOutputParser()
        
        response = chain.invoke({
            "program": program_data['name'],
            "semester": semester,
            "context": context,
            "question": question
        })
        
        return response + f"\n\n(Source: {program_data['keywords'][0].upper()} document)"

    def generate_response(self, question):
        """Enhanced response generation with better context handling"""
        program, program_data = self.detect_program(question)
        
        # Handle semester count questions
        if "how many semesters" in question.lower() and program_data:
            return f"{program_data['name']} has {program_data['duration']}.\n\n(Source: {program.upper()} program information)"
        
        # Handle course listing questions
        course_keywords = ["courses in semester", "list of courses", "course structure", 
                          "subjects in", "curriculum", "syllabus", "semester courses"]
        if any(phrase in question.lower() for phrase in course_keywords):
            if not program_data:
                return "Please specify which program (e.g., BCA, CSIT, BSW, BBS) you're asking about."
            return self._handle_course_listing(question, program_data)
        
        # Enhanced general query handling
        context = self.query_documents(question, program)
        
        if not context or len(context.strip()) < 10:
            # Try broader search
            context = self.query_documents(question, None, k=20)
        
        if not context or len(context.strip()) < 10:
            return "I couldn't find specific information about your question in the available documents. Could you try rephrasing your question or be more specific?"
        
        # Enhanced prompt for better responses
        prompt = ChatPromptTemplate.from_template("""
        You are a helpful assistant providing information about Samriddhi College and its programs.
        
        Available information:
        {context}
        
        Question: {question}
        
        Instructions:
        1. Provide a clear, helpful answer based on the available information
        2. Be specific and accurate
        3. If the information partially answers the question, provide what you can
        4. Use a conversational but professional tone
        5. Only say information is "not available" if you truly cannot find any relevant details
        6. Focus on being helpful rather than overly cautious
        
        Answer the question based on the provided context.
        """)
        
        chain = prompt | ChatGroq(
            temperature=0.3,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        ) | StrOutputParser()
        
        response = chain.invoke({
            "question": question,
            "context": context
        })
        
        # Add source attribution
        source = f"{program.upper()} document" if program else "Samriddhi College documents"
        return f"{response}\n\n(Source: {source})"

def interactive_chat():
    print("\n" + "="*60)
    print("SAMRIDDHI COLLEGE INFORMATION SYSTEM")
    print("="*60)
    print("Available Programs: BCA, CSIT (BSc CSIT), BSW, BBS")
    print("You can ask about:")
    print("- College information (principal, directors, facilities)")
    print("- Program details (duration, eligibility, career prospects)")
    print("- Course structure and semester-wise subjects")
    print("- Admission requirements and procedures")
    print("\nType 'exit' or 'quit' to end the session")
    print("="*60)
    
    system = CollegeQuerySystem()
    
    while True:
        try:
            question = input("\n💬 Your question: ").strip()
            
            if not question:
                print("Please enter a question.")
                continue
                
            if question.lower() in ['exit', 'quit', 'bye']:
                print("\nThank you for using Samriddhi College Information System! 👋")
                break
                
            print("\n🔍 Searching for information...")
            response = system.generate_response(question)
            print(f"\n📋 Answer:\n{response}")
            print("\n" + "-"*60)
            
        except KeyboardInterrupt:
            print("\n\nSession ended by user. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try asking your question differently.")

if __name__ == "__main__":
    interactive_chat()