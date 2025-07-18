import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
 # Updated import

load_dotenv()

class CSITQuerySystem:
    def __init__(self):
        """Initialize the query system with embeddings and paths"""
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectordb_path = "db"  # Directory for vector database
        self.md_path = "data/BSW.md"  # Path to markdown file
        
        # Verified institutional knowledge about programs
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
        """Create/update vector database from Markdown file"""
        try:
            print("Loading markdown documents...")
            loader = TextLoader(self.md_path)
            pages = loader.load_and_split()
            
            # Configure text splitting for markdown content
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", " ", ""]
            )
            splits = text_splitter.split_documents(pages)
            
            print("Creating vector database...")
            vectordb = Chroma.from_documents(
                documents=splits,
                embedding=self.embedding,
                persist_directory=self.vectordb_path
            )
            vectordb.persist()
            print("Vector database created successfully!")
            return vectordb
        except Exception as e:
            print(f"Error creating vector DB: {str(e)}")
            return None

    def get_vectordb(self):
        """Load existing vector database or create new if doesn't exist"""
        try:
            if not os.path.exists(self.vectordb_path):
                print("No existing vector DB found, creating new...")
                return self.create_vector_db()
            return Chroma(
                persist_directory=self.vectordb_path,
                embedding_function=self.embedding
            )
        except Exception as e:
            print(f"Error loading vector DB: {str(e)}")
            return None

    def _answer_college_query(self, prompt):
        """Handle specific questions about college programs"""
        prompt_lower = prompt.lower()
        
        # Program availability questions
        if any(q in prompt_lower for q in ["does samriddhi", "offer", "have", "provide"]):
            for program, details in self.college_programs.items():
                if any(kw in prompt_lower for kw in details["keywords"]):
                    if details["offered"]:
                        return (f"Yes, Samriddhi College offers {details['title']} ({details['duration']}) "
                                f"affiliated with {details['affiliation']}. Intake: {details['intake']} students. "
                                f"More info: {details['website']}")
                    return f"No, Samriddhi College does not currently offer {program.upper()}."
        
        # Program listing
        if "what programs" in prompt_lower or "which courses" in prompt_lower:
            offered = [details['title'] for details in self.college_programs.values() 
                      if details['offered']]
            return "Samriddhi College offers:\n- " + "\n- ".join(offered)
        
        return None

    def _query_md_content(self, prompt):
        """Query the markdown content using similarity search"""
        try:
            vectordb = self.get_vectordb()
            if not vectordb:
                return "Error: Could not access course documents."
                
            # Perform similarity search
            docs = vectordb.similarity_search(prompt, k=5)
            context = "\n".join([doc.page_content for doc in docs])
            
            # Initialize LLM
            llm = ChatGroq(
                temperature=0.2,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name="llama3-70b-8192"
            )
            
            # Generate response with strict context adherence
            response = llm.invoke(f"""Answer using ONLY this context:
                                {context}
                                Question: {prompt}
                                If the answer isn't here, respond: "This information is not in the program document".""")
            
            return response.content
        except Exception as e:
            return f"Error querying documents: {str(e)}"

    def get_response(self, prompt):
        """Main query interface"""
        # First handle institutional questions
        college_response = self._answer_college_query(prompt)
        if college_response:
            return college_response
            
        # Then query markdown content
        return self._query_md_content(prompt)

def interactive_chat():
    """Run interactive chat interface"""
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
    # Uncomment to rebuild vector database when markdown changes:
    # CSITQuerySystem().create_vector_db()
    
    interactive_chat()
