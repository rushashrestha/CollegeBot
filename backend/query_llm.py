import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

class CollegeQuerySystem:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectordb_path = "db"
        
        # Improved prompt templates
        self.prompt_templates = {
            "general": ChatPromptTemplate.from_template(
                """Answer the question based only on the following context from college documents:
                {context}
                
                Question: {question}
                Answer in complete sentences. If the information isn't available, say "This information isn't available in college documents"."""
            ),
            "table": ChatPromptTemplate.from_template(
                """Extract table data to answer: {question}
                Context: {context}
                Format your answer as:
                - Column1: Value1
                - Column2: Value2
                ..."""
            )
        }

    def get_vectordb(self):
        """Load existing vector database"""
        return Chroma(
            persist_directory=self.vectordb_path,
            embedding_function=self.embedding
        )

    def query_documents(self, question, k=5):
        """Enhanced document query with table detection"""
        vectordb = self.get_vectordb()
        docs = vectordb.similarity_search(question, k=k)
        return "\n\n".join([doc.page_content for doc in docs])

    def generate_response(self, question):
        """Handle all question types"""
        context = self.query_documents(question)
        
        # Detect table questions
        is_table_question = any(word in question.lower() for word in 
                              ["table", "list of", "courses in", "syllabus", "curriculum"])
        
        llm = ChatGroq(
            temperature=0.1,
            model_name="llama3-70b-8192",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        if is_table_question:
            chain = self.prompt_templates["table"] | llm
            return chain.invoke({"question": question, "context": context}).content
        else:
            chain = self.prompt_templates["general"] | llm
            return chain.invoke({"question": question, "context": context}).content

def interactive_chat():
    print("\nCollege Information System (Supports all question types)")
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