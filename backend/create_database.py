from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

def load_and_process_md_files(directory="data"):
    """Process all MD files with program-specific handling"""
    all_texts = []
    
    # Configuration for each program type
    program_config = {
        "bca": {
            "separators": ["\n\n", "\n## Semester", "Course Code:", "|", "\n- "],
            "chunk_size": 2000
        },
        "csit": {
            "separators": ["\n\n", "\n## Semester", "Course Title", "|", "\n• "],
            "chunk_size": 2500
        },
        "bsw": {
            "separators": ["\n\n", "\n##", "Course:", "|", "\n● "],
            "chunk_size": 1800
        },
        "bbs": {
            "separators": ["\n\n", "\n## Part", "|", "\n• "],
            "chunk_size": 1800
        }
    }

    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            program = filename.split('.')[0].lower()
            config = program_config.get(program, {
                "separators": ["\n\n", "\n##", "|"],
                "chunk_size": 1500
            })
            
            try:
                loader = TextLoader(f"{directory}/{filename}", encoding='utf-8')
                documents = loader.load()
                
                # Add dynamic semester separators (1-8)
                semester_seps = [f"\nSemester {i}" for i in range(1, 9)] + [f"\n{i} Semester" for i in range(1, 9)]
                separators = config["separators"] + semester_seps
                
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=config["chunk_size"],
                    chunk_overlap=300,
                    separators=separators
                )
                
                texts = text_splitter.split_documents(documents)
                
                # Add metadata
                for text in texts:
                    text.metadata.update({
                        "program": program,
                        "source": filename
                    })
                
                all_texts.extend(texts)
                print(f"Processed {filename} with {len(texts)} chunks")
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    return all_texts

def create_vector_store(texts):
    """Create and persist the vector database"""
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vectordb = Chroma.from_documents(
        documents=texts,
        embedding=embedding,
        persist_directory="db",
        collection_metadata={
            "hnsw:space": "cosine",
            "description": "College programs database"
        }
    )
    # vectordb.persist()
    return vectordb

if __name__ == "__main__":
    print("Processing all Markdown files...")
    texts = load_and_process_md_files()
    
    print("\nCreating vector database...")
    db = create_vector_store(texts)
    
    print(f"\nDatabase created successfully with {len(texts)} document chunks")
    print(f"Persisted to directory: db/")