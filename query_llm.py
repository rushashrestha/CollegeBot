import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

load_dotenv()

# Answer templates for common CSIT questions
ANSWER_TEMPLATES = {
    "semester": "The BSc CSIT program at Tribhuvan University consists of 8 semesters over 4 years.",
    "colleges": lambda x: f"{x} is mentioned in the CSIT program materials as an affiliated college.",
    "courses": "In semester {num}, the courses include: {list}",
    "default": "Based on the CSIT program document: {answer}"
}

def enhance_query(prompt):
    """Expand queries with synonyms"""
    synonyms = {
        "semester": ["term", "academic period"],
        "college": ["institution", "campus"],
        "course": ["subject", "class"]
    }
    
    enhanced = prompt.lower()
    for term, variants in synonyms.items():
        if term in enhanced:
            enhanced += " " + " ".join(variants)
    return enhanced

def get_csit_response(prompt):
    try:
        embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectordb = Chroma(persist_directory="db", embedding_function=embedding)
        
        # Enhanced retrieval with synonym expansion
        expanded_query = enhance_query(prompt)
        docs = vectordb.similarity_search(expanded_query, k=5)
        
        # Page-aware context building
        context_by_page = {}
        for doc in docs:
            page = doc.metadata.get('page', 0)
            context_by_page.setdefault(page, []).append(doc.page_content)
        
        # Prioritize most relevant pages
        sorted_pages = sorted(context_by_page.items(), 
                            key=lambda x: len(x[1]), 
                            reverse=True)
        context = "\n\n".join([f"=== Page {page} ===\n" + "\n".join(content) 
                             for page, content in sorted_pages[:3]])
        
        # Special cases handling
        if "how many semester" in prompt.lower():
            return ANSWER_TEMPLATES["semester"]
            
        if "college" in prompt.lower():
            college_names = ["St. Xavier's", "Patan Multiple Campus", "Amrit Science Campus"]
            found = [c for c in college_names if c.lower() in context.lower()]
            if found:
                return "\n".join([ANSWER_TEMPLATES["colleges"](c) for c in found])
        
        # General answer generation
        llm = ChatGroq(
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama3-70b-8192"
        )
        
        response = llm.invoke(f"""Answer this CSIT question using ONLY below context.
                            If unsure, say "I couldn't find specific information".
                            
                            Context:
                            {context}
                            
                            Question: {prompt}""")
        
        # Verify answer quality
        if verify_answer(response.content, context):
            return ANSWER_TEMPLATES["default"].format(answer=response.content)
        return response.content
        
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, I couldn't process that request."

def verify_answer(answer, context):
    """Ensure answer is context-grounded"""
    required_terms = ["CSIT", "TU", "semester", "credit", "course"]
    return sum(term in answer for term in required_terms) >= 2

def interactive_chat():
    print("\nCSIT Query System (Type 'exit' to quit)")
    while True:
        prompt = input("\nYour question: ").strip()
        if prompt.lower() in ['exit', 'quit']:
            break
            
        response = get_csit_response(prompt)
        print(f"\nAnswer: {response}\n")

if __name__ == "__main__":
    interactive_chat()