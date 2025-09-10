import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
import pandas as pd

load_dotenv()

class CSITQuerySystem:
    def __init__(self):
        # ========================
        # Embedding model
        # ========================
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        # Paths
        self.md_db_path = "db/md"           # Markdown/PDF data
        self.student_db_path = "db/student" # Student CSV data

        # Verified institutional knowledge
        self.college_programs = {
            "csit": {
                "offered": True,
                "title": "Bachelor of Science in Computer Science and IT",
                "duration": "4 years (8 semesters)",
                "affiliation": "Tribhuvan University",
                "intake": 48,
                "website": "https://samriddhicollege.edu.np/bsc-csit",
                "keywords": ["csit", "computer science", "bsc csit"]
            },
            "bca": {
                "offered": True,
                "title": "Bachelor of Computer Applications",
                "duration": "4 years",
                "affiliation": "Tribhuvan University",
                "intake": 60,
                "website": "https://samriddhicollege.edu.np/bca",
                "keywords": ["bca", "computer applications"]
            }
        }

    # ========================
    # Load Markdown / PDF Vector DB
    # ========================
    def get_md_vectordb(self):
        try:
            if not os.path.exists(self.md_db_path):
                return None
            return Chroma(
                persist_directory=self.md_db_path,
                embedding_function=self.embedding
            )
        except Exception as e:
            print(f"Error loading Markdown/PDF DB: {e}")
            return None

    # ========================
    # Load Student CSV Vector DB
    # ========================
    def get_student_db(self):
        try:
            if not os.path.exists(self.student_db_path) or not os.path.exists(os.path.join(self.student_db_path, "chroma.sqlite3")):
                return None
            return Chroma(
                persist_directory=self.student_db_path,
                embedding_function=self.embedding
            )
        except Exception as e:
            print(f"Error loading student DB: {e}")
            return None

    # ========================
    # College program Qs
    # ========================
    def _answer_college_query(self, prompt):
        prompt_lower = prompt.lower()
        if any(q in prompt_lower for q in ["does samriddhi", "offer", "have", "provide"]):
            for program, details in self.college_programs.items():
                if any(kw in prompt_lower for kw in details["keywords"]):
                    if details["offered"]:
                        return (f"Yes, Samriddhi College offers {details['title']} ({details['duration']}) "
                                f"affiliated with {details['affiliation']}. Intake: {details['intake']} students. "
                                f"More info: {details['website']}")
                    return f"No, Samriddhi College does not currently offer {program.upper()}."

        if "what programs" in prompt_lower or "which courses" in prompt_lower:
            offered = [details['title'] for details in self.college_programs.values() if details['offered']]
            return "Samriddhi College offers:\n- " + "\n- ".join(offered)

        return None

    # ========================
    # Query a Vector DB
    # ========================
    def _query_vectordb(self, vectordb, prompt, db_type="PDF/Markdown"):
        try:
            if not vectordb:
                return None

            docs = vectordb.similarity_search(prompt, k=5)
            if not docs:
                return None

            context = "\n".join([doc.page_content for doc in docs])
            llm = ChatGroq(
                temperature=0.1,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name="llama-3.3-70b-versatile"
            )

            response = llm.invoke(f"""Answer using ONLY this {db_type} context:
{context}
Question: {prompt}
If the answer isn't here, respond: "This information is not in the {db_type} database".""")
            return response.content
        except Exception as e:
            return f"Error querying {db_type} database: {str(e)}"

    # ========================
    # Main router for user queries
    # ========================
    def get_response(self, prompt):
        # 1. Institutional questions
        college_response = self._answer_college_query(prompt)
        if college_response:
            return college_response

        # 2. Student CSV
        student_db = self.get_student_db()
        student_response = self._query_vectordb(student_db, prompt, db_type="student")
        if student_response and "not in the student database" not in student_response.lower():
            return student_response

        # 3. Markdown / PDF
        md_db = self.get_md_vectordb()
        md_response = self._query_vectordb(md_db, prompt, db_type="PDF/Markdown")
        if md_response:
            return md_response

        return "Sorry, I could not find an answer to your question."

# ========================
# Interactive chat
# ========================
def interactive_chat():
    print("\nSamriddhi College Academic Query System")
    print("Type 'exit' to quit\n")

    system = CSITQuerySystem()

    while True:
        try:
            prompt = input("Your question: ").strip()
            if prompt.lower() in ['exit', 'quit']:
                break

            response = system.get_response(prompt)
            print(f"\n{response}\n")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {str(e)}\n")


if __name__ == "__main__":
    interactive_chat()
