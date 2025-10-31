import os
from dotenv import load_dotenv
import requests
from urllib.parse import quote_plus
import re
from datetime import datetime

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import torch
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ---------------- Supabase config ----------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

# ---------------- Helper utils ----------------
def _safe(val):
    if val is None:
        return "N/A"
    return str(val)

def _get_pronouns(gender):
    """Get appropriate pronouns based on gender"""
    if not gender or gender == "N/A":
        return {"subject": "they", "object": "them", "possessive": "their", "possessive_adj": "their"}
    
    gender_lower = str(gender).lower()
    if gender_lower in ["male", "m"]:
        return {"subject": "he", "object": "him", "possessive": "his", "possessive_adj": "his"}
    elif gender_lower in ["female", "f"]:
        return {"subject": "she", "object": "her", "possessive": "hers", "possessive_adj": "her"}
    else:
        return {"subject": "they", "object": "them", "possessive": "their", "possessive_adj": "their"}

def _sample_names(records, n=5):
    names = []
    for r in records:
        name = r.get("name")
        if name:
            names.append(name)
    return names[:n]

# ---------------- Main system ----------------
class CollegeQuerySystem:

    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectordb_path = "db"

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
                "duration": "4 years",
                "seats": 60,
                "keywords": ["bsw", "social work"]
            },
            "bbs": {
                "name": "Bachelor of Business Studies", 
                "duration": "4 years",
                "seats": 60,
                "keywords": ["bbs", "business studies"]
            }
        }

        # Define institutional roles that should be treated as document queries
        self.institutional_roles = [
            "principal", "vice principal", "director", "vice director",
            "chairman", "vice chairman", "dean", "head", "coordinator",
            "registrar", "controller", "chief", "president", "secretary"
        ]

    def _is_institutional_query(self, question):
        """Check if query is about institutional roles (from documents, not database)"""
        q_lower = question.lower()
        
        # Check for institutional role keywords
        if any(role in q_lower for role in self.institutional_roles):
            # Exclude specific person queries that want contact details
            exclude_patterns = ["email of", "phone of", "contact of", "address of"]
            if not any(pattern in q_lower for pattern in exclude_patterns):
                return True
        
        return False

    def _check_data_access(self, question, user_role="guest", user_data=None):
        """Check if the current user has access to the requested data"""
        q_lower = question.lower()
        
        # FIRST: Check if this is an institutional query (always allowed)
        if self._is_institutional_query(question):
            return True, None
        
        # Guest access restrictions
        if user_role == "guest":
            # Check if asking for specific person's detailed info
            restricted_patterns = [
                "email of", "phone of", "contact of", "address of", 
                "roll no", "roll number", "symbol number", "registration number", 
                "dob of", "date of birth of", "birthday of", "gender of",
                "batch of", "section of", "joined"
            ]
            
            has_restricted = any(pattern in q_lower for pattern in restricted_patterns)
            
            # Check if asking about a specific person (not institutional role)
            person_queries = ["who is", "information about", "details about", "tell me about"]
            is_person_query = any(query in q_lower for query in person_queries)
            
            # Extract potential name
            name = self._extract_person_name(question)
            
            # If it's asking for restricted info about a specific person
            if (has_restricted or (is_person_query and name)) and not self._is_institutional_query(question):
                return False, "Hmm, I can't share personal details like that without login. But I'd be happy to tell you about our programs, courses, or facilities!"
        
        # Student access restrictions
        elif user_role == "student" and user_data:
            name = self._extract_person_name(question)
            if name:
                student_name = user_data.get('name', '').lower() if user_data else ''
                searched_name = name.lower()
                
                # Allow own data
                if student_name and searched_name in student_name:
                    return True, None
                
                # Allow teacher data
                teacher_data = self._search_person(name)
                if teacher_data and teacher_data["type"] == "teacher":
                    return True, None
                
                # Deny other student data
                student_data = self._search_person(name)
                if student_data and student_data["type"] == "student":
                    return False, "I can only share your own information or teacher details. For privacy reasons, I can't show you other students' personal data."
        
        # Teachers and admins have full access
        return True, None

    def _query_supabase(self, table, params=None):
        if not SUPABASE_URL or not SUPABASE_KEY:
            return []

        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        
        query_params = {}
        if params:
            query_params.update(params)

        try:
            resp = requests.get(url, headers=headers, params=query_params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            return []

    def _extract_person_name(self, question):
        """Extract person name from various question formats"""
        q_lower = question.lower().strip()
        
        # Skip if institutional query
        if self._is_institutional_query(question):
            return None
        
        patterns_to_remove = [
            r'give\s+me\s+',
            r'tell\s+me\s+',
            r'show\s+me\s+',
            r'what\s+is\s+the\s+',
            r'what\s+is\s+',
            r'when\s+did\s+',
            r'when\s+does\s+',
            r'who\s+is\s+',
            r'information\s+about\s+',
            r'details\s+about\s+',
            r'email\s+of\s+',
            r'email\s+for\s+',
            r'phone\s+number\s+of\s+',
            r'phone\s+of\s+',
            r'contact\s+of\s+',
            r'contact\s+detail\s+of\s+',
            r'contact\s+details\s+of\s+',
            r'address\s+of\s+',
            r'roll\s+no\s+of\s+',
            r'roll\s+number\s+of\s+',
            r'symbol\s+number\s+of\s+',
            r'registration\s+number\s+of\s+',
            r'dob\s+of\s+',
            r'date\s+of\s+birth\s+of\s+',
            r'birthday\s+of\s+',
            r'age\s+of\s+',
            r'gender\s+of\s+',
            r'batch\s+of\s+',
            r'section\s+of\s+',
            r'\bthe\b',
            r'\bstudying\b',
            r'\bstudy\b',
            r'\bjoined\s+the\s+college\b',
            r'\bjoined\b',
            r'\bprogram\b',
            r'\bsection\b',
            r'\bbatch\b',
            r'\?',
            r'\bcollege\b'
        ]
        
        cleaned = q_lower
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, ' ', cleaned)
        
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        words = cleaned.split()
        if 1 <= len(words) <= 3:
            return ' '.join(words).strip()
        
        return None

    def _search_person(self, name):
        """Search for a person in both teachers and students tables"""
        if not name or len(name) < 2:
            return None
            
        students = self._query_supabase("students_data", params={"name": f"ilike.%{name}%"})
        if students:
            return {"type": "student", "data": students[0]}
        
        teachers = self._query_supabase("teachers_data", params={"name": f"ilike.%{name}%"})
        if teachers:
            return {"type": "teacher", "data": teachers[0]}
            
        return None

    def _get_person_info(self, person_data):
        """Get formatted information about a person in natural, flowing sentences"""
        if person_data["type"] == "student":
            s = person_data["data"]
            name = _safe(s.get('name'))
            gender = s.get('gender')
            pronouns = _get_pronouns(gender)
            
            program = _safe(s.get('program'))
            batch = _safe(s.get('batch'))
            section = _safe(s.get('section'))
            year_semester = _safe(s.get('year_semester'))
            roll_no = _safe(s.get('roll_no'))
            symbol_no = _safe(s.get('symbol_no'))
            registration_no = _safe(s.get('registration_no'))
            email = _safe(s.get('email'))
            phone = _safe(s.get('phone'))
            dob_ad = _safe(s.get('dob_ad'))
            dob_bs = _safe(s.get('dob_bs'))
            perm_address = _safe(s.get('perm_address'))
            temp_address = _safe(s.get('temp_address'))
            joined_date = _safe(s.get('joined_date'))
            
            # Build natural response
            intro = f"{name} is studying at Samriddhi College"
            
            if program != "N/A":
                intro += f", enrolled in the {program} program"
            
            if batch != "N/A" or section != "N/A":
                details = []
                if batch != "N/A":
                    details.append(f"batch {batch}")
                if section != "N/A":
                    details.append(f"section {section}")
                intro += f" ({', '.join(details)})"
            
            intro += "."
            
            # Add additional details naturally
            extra_info = []
            
            if year_semester != "N/A":
                extra_info.append(f"{pronouns['subject'].capitalize()}'s currently in {year_semester}")
            
            if roll_no != "N/A":
                extra_info.append(f"roll number {roll_no}")
            
            contact_parts = []
            if email != "N/A":
                contact_parts.append(f"email at {email}")
            if phone != "N/A":
                contact_parts.append(f"call at {phone}")
            
            if contact_parts:
                extra_info.append(f"you can reach {pronouns['object']} via {' or '.join(contact_parts)}")
            
            response = intro
            if extra_info:
                response += " " + ", and ".join(extra_info) + "."
            
            return response
            
        else:  # teacher
            t = person_data["data"]
            name = _safe(t.get('name'))
            gender = t.get('gender')
            pronouns = _get_pronouns(gender)
            
            designation = _safe(t.get('designation'))
            subject = _safe(t.get('subject'))
            degree = _safe(t.get('degree'))
            email = _safe(t.get('email'))
            phone = _safe(t.get('phone'))
            
            intro = f"{name} is a {designation.lower()} at Samriddhi College"
            
            if subject != "N/A":
                intro += f", teaching {subject}"
            
            intro += "."
            
            extra_info = []
            
            if degree != "N/A":
                extra_info.append(f"{pronouns['subject']} holds a {degree} degree")
            
            contact_parts = []
            if email != "N/A":
                contact_parts.append(f"email at {email}")
            if phone != "N/A":
                contact_parts.append(f"call at {phone}")
            
            if contact_parts:
                extra_info.append(f"you can contact {pronouns['object']} via {' or '.join(contact_parts)}")
            
            response = intro
            if extra_info:
                response += " " + ", and ".join(extra_info) + "."
            
            return response

    def _handle_specific_field_query(self, question, person_data):
        """Handle queries asking for specific fields with natural language"""
        q_lower = question.lower()
        data = person_data["data"]
        name = data.get('name', 'Unknown')
        
        if person_data["type"] == "student":
            if "email" in q_lower:
                email = data.get("email")
                if email and email != "N/A":
                    return f"You can reach {name} at {email}."
                return f"Sorry, I don't have an email address for {name}."
            
            if "phone" in q_lower or "contact number" in q_lower or "mobile" in q_lower:
                phone = data.get("phone")
                if phone and phone != "N/A":
                    return f"{name}'s phone number is {phone}."
                return f"I don't have phone information for {name}."
            
            if "roll no" in q_lower or "roll number" in q_lower:
                roll_no = data.get("roll_no")
                if roll_no and roll_no != "N/A":
                    return f"{name}'s roll number is {roll_no}."
                return f"I don't have roll number details for {name}."
            
            if any(word in q_lower for word in ["program", "studying", "study", "course"]):
                program = data.get("program")
                if program and program != "N/A":
                    return f"{name} is studying {program}."
                return f"I'm not sure what program {name} is in."
            
        else:  # teacher
            if "email" in q_lower:
                email = data.get("email")
                if email and email != "N/A":
                    return f"You can email {name} at {email}."
                return f"Sorry, I don't have an email for {name}."
            
            if "phone" in q_lower or "contact" in q_lower:
                phone = data.get("phone")
                if phone and phone != "N/A":
                    return f"{name}'s phone number is {phone}."
                return f"I don't have contact information for {name}."
            
            if "teach" in q_lower or "subject" in q_lower:
                subject = data.get("subject")
                if subject and subject != "N/A":
                    return f"{name} teaches {subject}."
                return f"I'm not sure what {name} teaches."
        
        return None

    def _handle_person_query(self, question):
        """Handle all types of person-related queries"""
        name = self._extract_person_name(question)
        if not name:
            return None
            
        print(f"🔍 Looking up: '{name}'")
        
        person_data = self._search_person(name)
        if not person_data:
            return f"Hmm, I couldn't find anyone named {name.title()} in our database. Could you double-check the spelling?"
        
        specific_response = self._handle_specific_field_query(question, person_data)
        if specific_response:
            return specific_response
        
        return self._get_person_info(person_data)

    def _handle_teacher_subject_query(self, question):
        """Handle 'who teaches X' queries"""
        q_lower = question.lower()
        
        subject = None
        if "who teaches" in q_lower:
            subject = q_lower.split("who teaches")[1].strip(" ?.")
        elif "who is teaching" in q_lower:
            subject = q_lower.split("who is teaching")[1].strip(" ?.")
        
        if not subject:
            return None
            
        print(f"🔍 Finding teacher for: '{subject}'")
        
        teachers = self._query_supabase("teachers_data", params={"subject": f"ilike.%{subject}%"})
        
        if not teachers:
            return f"I couldn't find information about who teaches {subject}. It might not be in our database yet."

        if len(teachers) == 1:
            t = teachers[0]
            name = _safe(t.get('name'))
            designation = _safe(t.get('designation'))
            return f"{name}, who's a {designation.lower()}, teaches {subject}."
        else:
            names = [f"{_safe(t.get('name'))}" for t in teachers]
            return f"{', '.join(names[:-1])} and {names[-1]} teach {subject}."

    def _is_student_list_query(self, question):
        """Check if this is specifically a student list query"""
        q_lower = question.lower()
        
        list_keywords = ["list students", "all students", "students list", "show students", "names of students"]
        if any(keyword in q_lower for keyword in list_keywords):
            return True
            
        if "students in" in q_lower and ("batch" in q_lower or any(program in q_lower for program in ["csit", "bca", "bsw", "bbs"])):
            return True
            
        return False

    def _extract_section_from_query(self, question):
        """Extract section (A, B, etc.) from the query"""
        q_lower = question.lower()
        
        section_match = re.search(r'\b(section\s*([A-Z]))\b', q_lower, re.IGNORECASE)
        if section_match:
            return section_match.group(2).upper()
        
        letter_match = re.search(r'\b([A-Z])\b', q_lower)
        if letter_match and letter_match.group(1) in ['A', 'B', 'C', 'D']:
            return letter_match.group(1).upper()
            
        return None

    def _handle_student_list_query(self, question):
        """Handle student list queries"""
        if not self._is_student_list_query(question):
            return None
            
        q_lower = question.lower()
        
        program_match = None
        for program, data in self.programs.items():
            if any(kw in q_lower for kw in data["keywords"]):
                program_match = program
                break
        
        batch_match = re.search(r'\b(20\d{2}[-]?[A-Z0-9]*)\b', q_lower)
        batch = batch_match.group(0) if batch_match else None
        
        section = self._extract_section_from_query(question)
        
        if program_match:
            params = {"program": f"ilike.%{program_match.upper()}%"}
            if batch:
                params["batch"] = f"ilike.%{batch}%"
                
            students = self._query_supabase("students_data", params=params)
            
            if section and students:
                students = [s for s in students if s.get('section', '').upper() == section]

            if students:
                program_name = self.programs[program_match]["name"]
                sample_names = _sample_names(students, 10)
                
                filters = []
                if batch:
                    filters.append(f"batch {batch}")
                if section:
                    filters.append(f"section {section}")
                
                filter_text = f" ({', '.join(filters)})" if filters else ""
                
                response = f"Found {len(students)} students in {program_name}{filter_text}:\n\n"
                response += "\n".join([f"• {name}" for name in sample_names])
                
                if len(students) > 10:
                    response += f"\n\n...and {len(students) - 10} more"
                
                return response
        
        return None

    def get_vectordb(self):
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
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 3 and not any(h in line.lower() for h in ['header', '---']):
                    lines.append(f"• {parts[2]} (Code: {parts[1]})")
                continue
            lines.append(line)
        return '\n'.join(lines)

    def query_documents(self, question, program=None, k=15):
        """Enhanced document querying with multiple search strategies"""
        vectordb = self.get_vectordb()

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

        docs = vectordb.similarity_search(question, k=k)
        if docs:
            raw_context = "\n\n".join([doc.page_content for doc in docs])
            return self._clean_table_formatting(raw_context)

        return ""

    def _extract_courses_directly(self, context, semester):
        """Directly extract courses from table data"""
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
        context = self.query_documents(
            f"courses curriculum syllabus {program_data['name']} semester",
            program=program_data['keywords'][0],
            k=20
        )

        semester = "1"
        words = question.split()
        for word in words:
            if word.isdigit() and 1 <= int(word) <= 8:
                semester = word
                break
            elif word.lower() in ["first", "1st"]:
                semester = "1"
            elif word.lower() in ["second", "2nd"]:
                semester = "2"

        courses = self._extract_courses_directly(context, semester)

        if courses:
            return (
                f"Here are the courses for {program_data['name']}, Semester {semester}:\n\n" +
                '\n'.join(courses)
            )

        return f"Sorry, I couldn't find the course list for semester {semester}. The information might not be available yet."

    def _handle_program_queries(self, question, program_data):
        """Handle program-specific queries"""
        q_lower = question.lower()
        
        if "how many semesters" in q_lower or ("semester" in q_lower and "how many" in q_lower):
            return f"The {program_data['name']} program runs for {program_data['duration']}."

        if "how many seats" in q_lower or "seat capacity" in q_lower or "intake" in q_lower:
            return f"We have {program_data['seats']} seats available for {program_data['name']}."

        course_keywords = ["courses in semester", "list of courses", "course structure",
                          "subjects in", "curriculum", "syllabus", "semester courses"]
        if any(phrase in q_lower for phrase in course_keywords):
            return self._handle_course_listing(question, program_data)

        return None

    def _classify_query_type(self, question):
        """Improved query classification"""
        q_lower = question.lower()
        
        # FIRST: Check institutional queries (principal, director, etc.)
        if self._is_institutional_query(question):
            return "document"
        
        # Check for "who teaches X" - NOT "who is X"
        if ("who teaches" in q_lower or "who is teaching" in q_lower) and "who is" not in q_lower:
            return "teacher_subject"
        
        # Check for specific person database queries
        person_field_keywords = [
            "email of", "phone of", "contact of", "address of",
            "roll no", "roll number", "symbol", "registration",
            "dob of", "birthday of", "gender of", "batch of", "section of"
        ]
        
        if any(keyword in q_lower for keyword in person_field_keywords):
            return "person"
        
        # Check for "who is" + person name (not institutional)
        if "who is" in q_lower:
            name = self._extract_person_name(question)
            if name and len(name) > 1:
                return "person"
        
        # Student list queries
        if self._is_student_list_query(question):
            return "student_list"
        
        # Student count queries
        count_queries = ["how many students", "number of students", "total students"]
        if any(phrase in q_lower for phrase in count_queries):
            return "student_count"
        
        # Program-specific queries
        program_queries = [
            "how many semesters", "duration", "course", "curriculum",
            "syllabus", "seats", "admission", "eligibility"
        ]
        if any(phrase in q_lower for phrase in program_queries):
            return "program_info"
        
        # Default to document query
        return "document"

    def generate_response(self, question, user_role="guest", user_data=None):
        """Main response generation with improved flow"""
        q_lower = question.lower().strip()
        print(f"🧠 Processing: '{question}'")
        print(f"👤 User role: {user_role}")
        
        query_type = self._classify_query_type(question)
        print(f"📊 Query type: {query_type}")

        # Check access permissions
        has_access, error_message = self._check_data_access(question, user_role, user_data)
        if not has_access:
            return error_message

        # Route to appropriate handler
        if query_type == "person":
            response = self._handle_person_query(question)
            if response:
                return response

        elif query_type == "teacher_subject":
            response = self._handle_teacher_subject_query(question)
            if response:
                return response

        elif query_type == "program_info":
            program, program_data = self.detect_program(question)
            if program_data:
                response = self._handle_program_queries(question, program_data)
                if response:
                    return response

        elif query_type == "student_list":
            response = self._handle_student_list_query(question)
            if response:
                return response

        elif query_type == "student_count":
            # Handle student count queries
            program_match = None
            for program, data in self.programs.items():
                if any(kw in q_lower for kw in data["keywords"]):
                    program_match = program
                    break
            
            if program_match:
                params = {"program": f"ilike.%{program_match.upper()}%"}
                students = self._query_supabase("students_data", params=params)
                
                if students:
                    program_name = self.programs[program_match]["name"]
                    return f"There are {len(students)} students currently enrolled in {program_name}."
                else:
                    return f"I couldn't find any students in that program right now."

        # Fall back to document-based search
        program, program_data = self.detect_program(question)
        context = self.query_documents(question, program, k=20)
        
        if not context or len(context.strip()) < 10:
            return "Hmm, I couldn't find specific information about that. Could you rephrase your question or ask about something else?"

        # Use LLM for natural response generation
        prompt_template = """You are a friendly assistant at Samriddhi College. Answer questions naturally and conversationally.

Context from documents:
{context}

Question: {question}

Instructions:
- Answer in a natural, conversational tone (like talking to a friend)
- Be helpful and informative
- Keep it concise but complete
- If info is partial, share what you know
- Don't use bullet points unless listing multiple items
- Don't be overly formal or robotic

Answer:"""
        
        prompt = ChatPromptTemplate.from_template(prompt_template)

        chain = prompt | ChatGroq(
            temperature=0.4,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        ) | StrOutputParser()

        response = chain.invoke({
            "question": question,
            "context": context
        })

        return response.strip()


def interactive_chat():
    print("\n" + "="*60)
    print("🎓 SAMRIDDHI COLLEGE CHATBOT")
    print("="*60)
    print("I can help you with:")
    print("  • College info (principal, directors, facilities)")
    print("  • Programs (BCA, CSIT, BSW, BBS)")
    print("  • Courses, admissions, and career info")
    print("  • Student & teacher details (with proper access)")
    print("\nType 'exit' to quit")
    print("="*60)

    system = CollegeQuerySystem()

    while True:
        try:
            question = input("\n💬 Ask me: ").strip()

            if not question:
                continue

            if question.lower() in ['exit', 'quit', 'bye', 'q']:
                print("\n👋 Thanks for chatting! Have a great day!")
                break

            print("\n🔍 Let me check that for you...")
            response = system.generate_response(question)
            print(f"\n✨ {response}")
            print("\n" + "-"*60)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Oops, something went wrong: {str(e)}")
            print("Let's try that again!")


if __name__ == "__main__":
    interactive_chat()