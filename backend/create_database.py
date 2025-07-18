from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

def load_and_process_md_files(directory="data"):
    """Load and process all MD files in directory"""
    all_texts = []
    md_files = [f for f in os.listdir(directory) if f.endswith('.md')]
    
    for md_file in md_files:
        try:
            loader = TextLoader(f"{directory}/{md_file}", encoding='utf-8')
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", "##", "|", "●", "•", "Course Code", "Semester"]
            )
            texts = text_splitter.split_documents(documents)
            all_texts.extend(texts)
            
            print(f"Processed {md_file} with {len(texts)} chunks")
        except Exception as e:
            print(f"Error processing {md_file}: {str(e)}")
    
    return all_texts

# Process all MD files
texts = load_and_process_md_files()

# Create vector store
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma.from_documents(
    texts, 
    embedding, 
    persist_directory="db",
    collection_metadata={"hnsw:space": "cosine"}
)
vectordb.persist()
print("Vector database created with all MD files!")