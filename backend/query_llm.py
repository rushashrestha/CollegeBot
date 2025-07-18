import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from flask import Flask,request,jsonify

from flask_cors import CORS

load_dotenv()

app=Flask(__name__)
CORS(app)

@app.route('/api/query',methods=['POST','OPTIONS'])
def handle_query():
    if request.method=='OPTIONS':
        return jsonify({'status':'ok'}),200
    data=request.get_json()
    prompt=data['query']
    system=CSITQuerySystem()
    response=system.get_response(prompt)
    return jsonify({'response':response})

class CSITQuerySystem:
    def __init__(self):
        # Initialize with updated Chroma
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectordb_path = "data/scraped_pdfs/vector_db"
        self.pdf_path = "data/scraped_pdfs/full_csit_program.pdf"
        
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

    def create_vector_db(self):
        """Create/update vector database from PDF"""
        try:
            loader = PyPDFLoader(self.pdf_path)
            pages = loader.load_and_split()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", " ", ""]
            )
            splits = text_splitter.split_documents(pages)
            
            vectordb = Chroma.from_documents(
                documents=splits,
                embedding=self.embedding,
                persist_directory=self.vectordb_path
            )
            vectordb.persist()
            return vectordb
        except Exception as e:
            print(f"Error creating vector DB: {str(e)}")
            return None

    def get_vectordb(self):
        """Load existing vector database"""
        try:
            if not os.path.exists(self.vectordb_path):
                return self.create_vector_db()
            return Chroma(
                persist_directory=self.vectordb_path,
                embedding_function=self.embedding
            )
        except Exception as e:
            print(f"Error loading vector DB: {str(e)}")
            return None

    def _answer_college_query(self, prompt):
        """Handle questions about Samriddhi College programs"""
        prompt_lower = prompt.lower()
        
        # Check for program existence questions
        if any(q in prompt_lower for q in ["does samriddhi", "offer", "have", "provide"]):
            for program, details in self.college_programs.items():
                if any(kw in prompt_lower for kw in details["keywords"]):
                    if details["offered"]:
                        return (f"Yes, Samriddhi College offers {details['title']} ({details['duration']}) "
                            f"affiliated with {details['affiliation']}. Intake: {details['intake']} students. "
                            f"More info: {details['website']}")
                    return f"No, Samriddhi College does not currently offer {program.upper()}."
        
        # List available programs
        if "what programs" in prompt_lower or "which courses" in prompt_lower:
            offered = [details['title'] for details in self.college_programs.values() 
                      if details['offered']]
            return "Samriddhi College offers:\n- " + "\n- ".join(offered)
        
        return None

    def _query_pdf_content(self, prompt):
        """Query the PDF content for academic information"""
        try:
            vectordb = self.get_vectordb()
            if not vectordb:
                return "Unable to access course documents."
                
            docs = vectordb.similarity_search(prompt, k=5)
            context = "\n".join([doc.page_content for doc in docs])
            
            llm = ChatGroq(
                temperature=0.2,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name="llama3-70b-8192"
            )
            
            response = llm.invoke(f"""Answer using ONLY this context:
                                {context}
                                Question: {prompt}
                                If the answer isn't here, respond: "This information is not in the program document".""")
            
            return response.content
        except Exception as e:
            return f"Error querying documents: {str(e)}"

    def get_response(self, prompt):
        """Main method to get responses"""
        # First try institutional questions
        college_response = self._answer_college_query(prompt)
        if college_response:
            return college_response
            
        # Fall back to PDF content
        return self._query_pdf_content(prompt)

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
    # First-time setup (uncomment when PDF changes)
    # CSITQuerySystem().create_vector_db()
    
    app.run(host='0.0.0.0',port=5000,debug=True)