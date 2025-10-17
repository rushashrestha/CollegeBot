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

    def _check_data_access(self, question, user_role="guest", user_data=None):
        """Check if the current user has access to the requested data"""
        q_lower = question.lower()
        
        # Guest access restrictions - ONLY apply if user is actually a guest
        if user_role == "guest":
            restricted_patterns = [
                "email", "phone", "contact", "address", "roll no", "roll number",
                "symbol number", "registration number", "dob", "date of birth",
                "birthday", "gender", "batch", "section", "joined", "admission"
            ]
            
            # Check if question contains any restricted patterns
            has_restricted = any(pattern in q_lower for pattern in restricted_patterns)
            
            # Check if it's specifically asking about a person (who is, information about, etc.)
            person_queries = ["who is", "information about", "details about", "tell me about"]
            is_person_query = any(query in q_lower for query in person_queries)
            
            # If it contains restricted patterns OR is asking about a specific person
            if has_restricted or is_person_query:
                return False, "Guest users can only access general college information like programs, courses, and facilities. Please log in for detailed personal data."
        
        # Student access restrictions - ONLY for student role
        elif user_role == "student" and user_data:
            # Extract person name from question
            name = self._extract_person_name(question)
            if name:
                # Students can access their own data and teacher data
                student_name = user_data.get('name', '').lower() if user_data else ''
                searched_name = name.lower()
                
                # Allow access to own data
                if student_name and searched_name in student_name:
                    return True, None
                
                # Allow access to teacher data
                teacher_data = self._search_person(name)
                if teacher_data and teacher_data["type"] == "teacher":
                    return True, None
                
                # Deny access to other student data
                student_data = self._search_person(name)
                if student_data and student_data["type"] == "student":
                    return False, "Students can only access their own information and teacher details. You cannot view other students' personal information."
        
        # Teachers and admins have full access
        elif user_role in ["teacher", "admin"]:
            return True, None
        
        # ALLOW access for authenticated users (student, teacher, admin) for general queries
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
        """Extract person name from various question formats - IMPROVED"""
        q_lower = question.lower().strip()
        
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
            r'contact\s+detail\s+of\s+',  # ADDED: handle "contact detail of"
            r'contact\s+details\s+of\s+', # ADDED: handle "contact details of"
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
        """Get formatted information about a person in human-like sentences"""
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
            
            sentences = [f"{name} is a student at Samriddhi College."]
            
            if program != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} is enrolled in the {program} program.")
            
            if batch != "N/A" and section != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} is in batch {batch}, section {section}.")
            elif batch != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} is in batch {batch}.")
            elif section != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} is in section {section}.")
            
            if year_semester != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} is currently in {year_semester}.")
            
            if roll_no != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} roll number is {roll_no}.")
            
            if symbol_no != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} symbol number is {symbol_no}.")
            
            if registration_no != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} registration number is {registration_no}.")
            
            if email != "N/A":
                sentences.append(f"You can contact {pronouns['object']} at {email}.")
            
            if phone != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} phone number is {phone}.")
            
            if dob_ad != "N/A" and dob_bs != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} date of birth is {dob_ad} (AD) / {dob_bs} (BS).")
            elif dob_ad != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} date of birth is {dob_ad}.")
            elif dob_bs != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} date of birth is {dob_bs} (BS).")
            
            if perm_address != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} permanent address is {perm_address}.")
            
            if temp_address != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} temporary address is {temp_address}.")
            
            if joined_date != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} joined the college on {joined_date}.")
            
            return " ".join(sentences)
        else:
            t = person_data["data"]
            name = _safe(t.get('name'))
            gender = t.get('gender')
            pronouns = _get_pronouns(gender)
            
            designation = _safe(t.get('designation'))
            subject = _safe(t.get('subject'))
            degree = _safe(t.get('degree'))
            email = _safe(t.get('email'))
            phone = _safe(t.get('phone'))
            address = _safe(t.get('address'))
            
            sentences = [f"{name} is a {designation.lower()} at Samriddhi College."]
            
            if subject != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} teaches {subject}.")
            
            if degree != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} holds a {degree} degree.")
            
            if email != "N/A":
                sentences.append(f"{pronouns['possessive_adj'].capitalize()} email address is {email}.")
            
            if phone != "N/A":
                sentences.append(f"You can reach {pronouns['object']} at {phone}.")
            
            if address != "N/A":
                sentences.append(f"{pronouns['subject'].capitalize()} resides at {address}.")
            
            return " ".join(sentences)

    def _handle_specific_field_query(self, question, person_data):
        """Handle queries asking for specific fields"""
        q_lower = question.lower()
        data = person_data["data"]
        name = data.get('name', 'Unknown')
        
        if person_data["type"] == "student":
            gender = data.get('gender')
            pronouns = _get_pronouns(gender)
            
            if "email" in q_lower:
                email = data.get("email")
                if email and email != "N/A":
                    return f"The email address for {name} is {email}."
                return f"I don't have email information for {name}."
            
            if "phone" in q_lower or "contact number" in q_lower or "mobile" in q_lower:
                phone = data.get("phone")
                if phone and phone != "N/A":
                    return f"{name}'s phone number is {phone}."
                return f"I don't have phone information for {name}."
            
            if "roll no" in q_lower or "roll number" in q_lower:
                roll_no = data.get("roll_no")
                if roll_no and roll_no != "N/A":
                    return f"The roll number for {name} is {roll_no}."
                return f"I don't have roll number information for {name}."
            
            if "symbol" in q_lower and "number" in q_lower:
                symbol_no = data.get("symbol_no")
                if symbol_no and symbol_no != "N/A":
                    return f"{name}'s symbol number is {symbol_no}."
                return f"I don't have symbol number information for {name}."
            
            if "registration" in q_lower and "number" in q_lower:
                reg_no = data.get("registration_no")
                if reg_no and reg_no != "N/A":
                    return f"{name}'s registration number is {reg_no}."
                return f"I don't have registration number information for {name}."
            
            if any(word in q_lower for word in ["program", "studying", "study", "course"]):
                program = data.get("program")
                if program and program != "N/A":
                    return f"{name} is studying {program}."
                return f"I don't have program information for {name}."
            
            if "batch" in q_lower or "section" in q_lower:
                batch = data.get("batch")
                section = data.get("section")
                parts = []
                if batch and batch != "N/A":
                    parts.append(f"batch {batch}")
                if section and section != "N/A":
                    parts.append(f"section {section}")
                if parts:
                    return f"{name} is in {' and '.join(parts)}."
                return f"I don't have batch/section information for {name}."
            
            if any(word in q_lower for word in ["dob", "date of birth", "birthday", "born"]):
                dob_ad = data.get("dob_ad")
                dob_bs = data.get("dob_bs")
                if dob_ad and dob_ad != "N/A":
                    if dob_bs and dob_bs != "N/A":
                        return f"{name}'s date of birth is {dob_ad} (AD) or {dob_bs} (BS)."
                    return f"{name}'s date of birth is {dob_ad}."
                elif dob_bs and dob_bs != "N/A":
                    return f"{name}'s date of birth is {dob_bs} (BS)."
                return f"I don't have date of birth information for {name}."
            
            if "gender" in q_lower or "boy" in q_lower or "girl" in q_lower or "male" in q_lower or "female" in q_lower:
                gender_val = data.get("gender")
                if gender_val and gender_val != "N/A":
                    return f"{name} is {gender_val.lower()}."
                return f"I don't have gender information for {name}."
            
            if "address" in q_lower:
                if "permanent" in q_lower:
                    perm_addr = data.get("perm_address")
                    if perm_addr and perm_addr != "N/A":
                        return f"{name}'s permanent address is {perm_addr}."
                    return f"I don't have permanent address information for {name}."
                elif "temporary" in q_lower or "temp" in q_lower:
                    temp_addr = data.get("temp_address")
                    if temp_addr and temp_addr != "N/A":
                        return f"{name}'s temporary address is {temp_addr}."
                    return f"I don't have temporary address information for {name}."
                else:
                    perm_addr = data.get("perm_address")
                    temp_addr = data.get("temp_address")
                    if perm_addr and perm_addr != "N/A":
                        return f"{name}'s permanent address is {perm_addr}."
                    elif temp_addr and temp_addr != "N/A":
                        return f"{name}'s temporary address is {temp_addr}."
                    return f"I don't have address information for {name}."
            
            if "joined" in q_lower or "join date" in q_lower or "admission date" in q_lower:
                joined = data.get("joined_date")
                if joined and joined != "N/A":
                    return f"{name} joined the college on {joined}."
                return f"I don't have joining date information for {name}."
        else:
            if "email" in q_lower:
                email = data.get("email")
                if email and email != "N/A":
                    return f"The email address for {name} is {email}."
                return f"I don't have email information for {name}."
            
            if "phone" in q_lower or "contact" in q_lower or "mobile" in q_lower:
                phone = data.get("phone")
                if phone and phone != "N/A":
                    return f"{name}'s phone number is {phone}."
                return f"I don't have phone information for {name}."
            
            if "address" in q_lower:
                address = data.get("address")
                if address and address != "N/A":
                    return f"{name} resides at {address}."
                return f"I don't have address information for {name}."
            
            if "teach" in q_lower or "subject" in q_lower:
                subject = data.get("subject")
                if subject and subject != "N/A":
                    return f"{name} teaches {subject}."
                return f"I don't have subject information for {name}."
            
            if "degree" in q_lower or "qualification" in q_lower or "education" in q_lower:
                degree = data.get("degree")
                if degree and degree != "N/A":
                    return f"{name} holds a {degree} degree."
                return f"I don't have degree information for {name}."
            
            if "designation" in q_lower or "position" in q_lower or "role" in q_lower:
                designation = data.get("designation")
                if designation and designation != "N/A":
                    return f"{name} is a {designation.lower()} at Samriddhi College."
                return f"I don't have designation information for {name}."
        
        return None

    def _handle_person_query(self, question):
        """Handle all types of person-related queries"""
        name = self._extract_person_name(question)
        if not name:
            return None
            
        print(f"🔍 Searching for person: '{name}'")
        
        person_data = self._search_person(name)
        if not person_data:
            return f"I couldn't find anyone named {name.title()} in our records. Could you check the spelling or provide more details?"
        
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
        elif "teaches" in q_lower:
            subject = q_lower.split("teaches")[1].strip(" ?.")
        
        if not subject:
            return None
            
        print(f"🔍 Searching for teacher of subject: '{subject}'")
        
        teachers = self._query_supabase("teachers_data", params={"subject": f"ilike.%{subject}%"})
        
        if not teachers:
            return f"I couldn't find information about who teaches {subject}. The subject might be taught by multiple faculty members or the information might not be available in our database."

        parts = []
        for t in teachers:
            name = _safe(t.get('name'))
            designation = _safe(t.get('designation'))
            parts.append(f"{name} ({designation})")
            
        if len(parts) == 1:
            return f"{parts[0]} teaches {subject}."
        elif len(parts) > 1:
            return f"{', '.join(parts[:-1])} and {parts[-1]} teach {subject}."
        
        return None

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
        """Handle ONLY explicit student list queries with section filtering"""
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
                section_students = []
                for student in students:
                    student_section = student.get('section', '').upper()
                    if student_section == section:
                        section_students.append(student)
                students = section_students

            if students:
                program_name = self.programs[program_match]["name"]
                sample_names = _sample_names(students, 10)
                
                if batch and section:
                    response = f"I found {len(students)} students in {program_name}, batch {batch}, section {section}:\n\n"
                elif batch:
                    response = f"I found {len(students)} students in {program_name}, batch {batch}:\n\n"
                elif section:
                    response = f"I found {len(students)} students in {program_name}, section {section}:\n\n"
                else:
                    response = f"I found {len(students)} students in the {program_name} program:\n\n"
                
                response += "\n".join([f"• {name}" for name in sample_names])
                
                if len(students) > 10:
                    response += f"\n\n... and {len(students) - 10} more students"
                
                return response
            else:
                program_name = self.programs[program_match]["name"]
                if batch and section:
                    return f"I couldn't find any students in {program_name}, batch {batch}, section {section}."
                elif batch:
                    return f"I couldn't find any students in {program_name}, batch {batch}."
                elif section:
                    return f"I couldn't find any students in {program_name}, section {section}."
                else:
                    return f"I couldn't find any students in the {program_name} program."
        
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
        context = self.query_documents(
            f"courses curriculum syllabus {program_data['name']} semester",
            program=program_data['keywords'][0],
            k=20
        )

        semester = "1"
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

        courses = self._extract_courses_directly(context, semester)

        if courses:
            return (
                f"Here are the courses for {program_data['name']}, Semester {semester}:\n\n" +
                '\n'.join(courses) +
                f"\n\n(Source: {program_data['keywords'][0].upper()} curriculum document)"
            )

        prompt_template = """You are a helpful assistant that extracts course information from college documents.

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
"""
        prompt = ChatPromptTemplate.from_template(prompt_template)

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

    def _handle_program_queries(self, question, program_data):
        """Handle program-specific queries with natural responses"""
        q_lower = question.lower()
        
        if "how many semesters" in q_lower or ("semester" in q_lower and "how many" in q_lower):
            return f"The {program_data['name']} program runs for {program_data['duration']}."

        if "how many seats" in q_lower or "seat capacity" in q_lower or "intake" in q_lower:
            return f"The {program_data['name']} program has {program_data['seats']} seats available."

        course_keywords = ["courses in semester", "list of courses", "course structure",
                          "subjects in", "curriculum", "syllabus", "semester courses"]
        if any(phrase in q_lower for phrase in course_keywords):
            return self._handle_course_listing(question, program_data)

        return None

    def _classify_query_type(self, question):
        """Classify the query type to ensure proper routing"""
        q_lower = question.lower()
        
        teacher_phrases = ["who teaches", "who is teaching"]
        if any(phrase in q_lower for phrase in teacher_phrases):
            if not any(p in q_lower for p in ["who is", "tell me about", "information about"]):
                return "teacher_subject"
        
        person_trigger_phrases = [
            "who is", "tell me about", "information about", "details about",
            "email of", "email for", "phone of", "phone number of", "contact of",
            "address of", "roll no of", "roll number of", "symbol number of",
            "registration number of", "dob of", "date of birth of", "birthday of",
            "age of", "gender of", "batch of", "section of", "when did", "when is the", "joined",
            "give me", "tell me", "show me", "what is the"
        ]
        
        has_person_trigger = any(phrase in q_lower for phrase in person_trigger_phrases)
        
        name = self._extract_person_name(question)
        
        if name and len(name) > 1:
            person_field_keywords = [
                "email", "phone", "address", "roll no", "roll number", "symbol", "registration",
                "dob", "birthday", "gender", "batch", "section", "program", "studying",
                "study", "joined", "join date", "admission date", "contact", "mobile"
            ]
            
            if has_person_trigger or any(keyword in q_lower for keyword in person_field_keywords):
                return "person"
        
        if not has_person_trigger and not name:
            program_queries = [
                "how many semesters", "duration", "course", "curriculum",
                "syllabus", "credit", "admission", "eligibility",
                "fee", "career", "opportunity", "faculty", "facilities"
            ]
            if any(phrase in q_lower for phrase in program_queries):
                return "program_info"
        
        if self._is_student_list_query(question):
            return "student_list"
        
        count_queries = ["how many students", "number of students", "total students"]
        if any(phrase in q_lower for phrase in count_queries):
            return "student_count"
        
        return "document"

    

    def generate_response(self, question, user_role="guest", user_data=None):
        q_lower = question.lower().strip()
        print(f"🧠 Processing: '{question}'")
        print(f"👤 User role: {user_role}")
        query_type = self._classify_query_type(question)
        print(f"📊 Query classified as: {query_type}")

        # ADD THIS ACCESS CHECK AT THE BEGINNING
        has_access, error_message = self._check_data_access(question, user_role, user_data)
        if not has_access:
            return error_message

        if query_type == "person":
            person_response = self._handle_person_query(question)
            if person_response:
                return person_response

        elif query_type == "teacher_subject":
            teacher_response = self._handle_teacher_subject_query(question)
            if teacher_response:
                return teacher_response

        elif query_type == "program_info":
            program, program_data = self.detect_program(question)
            if program_data:
                program_response = self._handle_program_queries(question, program_data)
                if program_response:
                    return program_response

        elif query_type == "student_list":
            student_list_response = self._handle_student_list_query(question)
            if student_list_response:
                return student_list_response

        elif query_type == "student_count":
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
                    section_students = []
                    for student in students:
                        student_section = student.get('section', '').upper()
                        if student_section == section:
                            section_students.append(student)
                    students = section_students

                if students:
                    program_name = self.programs[program_match]["name"]
                    if batch and section:
                        return f"There are {len(students)} students in {program_name}, batch {batch}, section {section}."
                    elif batch:
                        return f"There are {len(students)} students in {program_name}, batch {batch}."
                    elif section:
                        return f"There are {len(students)} students in {program_name}, section {section}."
                    else:
                        return f"There are {len(students)} students in the {program_name} program."
                else:
                    program_name = self.programs[program_match]["name"]
                    if batch and section:
                        return f"I couldn't find any students in {program_name}, batch {batch}, section {section}."
                    elif batch:
                        return f"I couldn't find any students in {program_name}, batch {batch}."
                    elif section:
                        return f"I couldn't find any students in {program_name}, section {section}."
                    else:
                        return f"I couldn't find any students in the {program_name} program."

        program, program_data = self.detect_program(question)
        context = self.query_documents(question, program)
        
        if not context or len(context.strip()) < 10:
            context = self.query_documents(question, None, k=20)

        if not context or len(context.strip()) < 10:
            return "I couldn't find specific information about your question in our records. Could you try rephrasing or providing more details?"

        prompt_template = """You are a helpful and friendly assistant providing information about Samriddhi College and its programs.

Available information from college documents:
{context}

Question: {question}

Instructions:
1. Provide a clear, helpful answer based ONLY on the available information
2. Use natural, conversational language - avoid robotic or technical phrasing
3. Be specific and accurate - cite specific details when possible
4. If the information partially answers the question, provide what you can
5. If you cannot find the answer in the provided context, say so clearly and politely

Answer the question in a friendly, helpful tone:
"""
        prompt = ChatPromptTemplate.from_template(prompt_template)

        chain = prompt | ChatGroq(
            temperature=0.3,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        ) | StrOutputParser()

        response = chain.invoke({
            "question": question,
            "context": context
        })

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
    print("- Teacher and student information (all database fields)")
    print("  • Students: name, email, phone, roll no, symbol no, registration no,")
    print("    program, batch, section, DOB, address, gender, joined date")
    print("  • Teachers: name, email, phone, subject, designation, degree, address")
    print("\nType 'exit' to end the session")
    print("="*60)

    system = CollegeQuerySystem()

    while True:
        try:
            question = input("\n💬 Your question: ").strip()

            if not question:
                continue

            if question.lower() in ['exit', 'quit', 'bye']:
                print("\nThank you for using our system! Have a great day! 👋")
                break

            print("\n🔍 Searching for information...")
            response = system.generate_response(question)
            print(f"\n📋 Answer:\n{response}")
            print("\n" + "-"*60)

        except KeyboardInterrupt:
            print("\n\nSession ended. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again.")


if __name__ == "__main__":
    interactive_chat()