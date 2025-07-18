import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

class MarkdownQuerySystem:
    def __init__(self):
        # MODIFY HERE: Update these paths to your Markdown files
        
        self.vectordb_path = "data/markdown/vector_db"  # Where to store ChromaDB
        self.md_paths = [
            "data/csit.md",  # Replace with your MD files
            "data/bca.md"
        ]
        
        # Initialize embedding model (no changes needed)
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # MODIFY HERE: Add/update your institutional knowledge
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


            },
            # Add other programs as needed
        }

    def create_vector_db(self):
        """Create/update vector database from Markdown files"""
        try:
            # Load all Markdown files
            documents = []
            for path in self.md_paths:
                loader = UnstructuredMarkdownLoader(path)
                documents.extend(loader.load())
            
            # MODIFY HERE: Adjust chunking parameters if needed
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,      # Optimal for most Markdown
                chunk_overlap=200,    # Helps maintain context
                separators=["\n\n## ", "\n### ", "\n• ", "\n- ", "\n```", "\n\n"]  # MD-specific
            )
            splits = text_splitter.split_documents(documents)
            
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
        """Handle institutional questions"""
        prompt_lower = prompt.lower()
        
        # MODIFY HERE: Update your institutional logic if needed
        if any(q in prompt_lower for q in ["does samriddhi", "offer", "have"]):
            for program, details in self.college_programs.items():
                if any(kw in prompt_lower for kw in details["keywords"]):
                    if details["offered"]:
                        return (f"Yes, we offer {details['title']} ({details['duration']}). "
                               f"More info: {details['website']}")
                    return f"No, we don't currently offer {program.upper()}."
        
        if "what programs" in prompt_lower:
            offered = [details['title'] for details in self.college_programs.values()]
            return "We offer:\n- " + "\n- ".join(offered)
        
        return None

    def _query_markdown_content(self, prompt):
        """Query the Markdown content"""
        try:
            vectordb = self.get_vectordb()
            if not vectordb:
                return "Database not available. Please try again later."
                
            # MODIFY HERE: Adjust retrieval parameters
            docs = vectordb.similarity_search(prompt, k=5)  # Top 5 most relevant chunks
            context = "\n".join([doc.page_content for doc in docs])
            
            # Initialize LLM (no changes needed)
            llm = ChatGroq(
                temperature=0.2,  # Lower = more factual
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name="llama3-70b-8192"  # MODIFY HERE: Change model if needed
            )
            
            # MODIFY HERE: Customize the prompt template
            response = llm.invoke(f"""Answer the question based ONLY on this context:
                                {context}
                                
                                Question: {prompt}
                                If unsure, say "I couldn't find this in the documents".""")
            
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"

    def get_response(self, prompt):
        """Main query handler"""
        # First check institutional knowledge
        college_response = self._answer_college_query(prompt)
        if college_response:
            return college_response
            
        # Fall back to document content
        return self._query_markdown_content(prompt)

def interactive_chat():
    """Run the chat interface"""
    print("\nAcademic Query System (Markdown)")
    print("Type 'exit' to quit\n")
    
    system = MarkdownQuerySystem()
    
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

if __name__ == "__main__":
    # First-time setup (uncomment to recreate vector DB when files change)
    # MarkdownQuerySystem().create_vector_db()
    
    interactive_chat()