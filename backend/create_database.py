#create_database.py
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from supabase import create_client, Client 
import shutil 
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
STORAGE_BUCKET = "college-documents"

def download_files_from_supabase():
    """Download all .md files from Supabase Storage to local data/ folder"""
    print("📥 Downloading files from Supabase Storage...")
    
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Create data directory if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")
        print("✅ Created 'data' directory")
    
    try:
        # List all files in storage bucket
        files = supabase.storage.from_(STORAGE_BUCKET).list()
        
        md_files_downloaded = 0
        
        for file_obj in files:
            filename = file_obj['name'] if isinstance(file_obj, dict) else getattr(file_obj, 'name', None)
            
            if filename and filename.endswith('.md'):
                try:
                    # Download file content
                    file_data = supabase.storage.from_(STORAGE_BUCKET).download(filename)
                    
                    # Save to local data/ folder
                    with open(f"data/{filename}", 'wb') as f:
                        f.write(file_data)
                    
                    print(f"✅ Downloaded: {filename}")
                    md_files_downloaded += 1
                    
                except Exception as e:
                    print(f"❌ Error downloading {filename}: {e}")
        
        print(f"\n📁 Total files downloaded: {md_files_downloaded}")
        return md_files_downloaded
        
    except Exception as e:
        print(f"❌ Error accessing Supabase Storage: {e}")
        return 0


def load_and_process_md_files(directory="data"):
    all_texts = []
    program_config = {
        "samriddhi": {
            "separators": ["\n### ", "\n## ", "\n# ", "\n\n", ":\n", "\n- "],
            "chunk_size": 1000,
            "chunk_overlap": 200
        },
        "csit": {
            "separators": ["\n## Semester", "\n### ", "\n## ", "| Course Code |", "\n\n", "●", "\n- "],
            "chunk_size": 1500,
            "chunk_overlap": 300
        },
        "bca": {
            "separators": ["\n## Semester", "\n### ", "\n## ", "| Course Code |", "\n\n", "\n- "],
            "chunk_size": 1500,
            "chunk_overlap": 300
        },
        "bsw": {
            "separators": ["\n## ", "\n### ", "| Course Code |", "\n\n", "\n- "],
            "chunk_size": 1200,
            "chunk_overlap": 250
        },
        "bbs": {
            "separators": ["\n# ", "\n## ", "| Course Code |", "\n\n", "\n- "],
            "chunk_size": 1200,
            "chunk_overlap": 250
        }
    }

    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            program = filename.split('.')[0].lower()
            config = program_config.get(program, {
                "separators": ["\n\n", "\n##", "\n#"],
                "chunk_size": 1000,
                "chunk_overlap": 200
            })
            
            try:
                loader = TextLoader(f"{directory}/{filename}", encoding='utf-8')
                documents = loader.load()
                
                base_separators = config["separators"].copy()
                
                semester_seps = []
                for i in range(1, 9):
                    semester_seps.extend([
                        f"\n## Semester {i}",
                        f"\n# Semester {i}",
                        f"\nSemester {i}",
                        f"\n{i} Semester"
                    ])
                
                year_seps = [f"\n# {year} Year" for year in ["First", "Second", "Third", "Fourth", "Forth"]]
                
                all_separators = base_separators + semester_seps + year_seps
                
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=config["chunk_size"],
                    chunk_overlap=config["chunk_overlap"],
                    separators=all_separators,
                    length_function=len,
                    is_separator_regex=False
                )
                
                texts = text_splitter.split_documents(documents)
                
                for i, text in enumerate(texts):
                    content = text.page_content.lower()
                    
                    chunk_type = "general"
                    if "semester" in content:
                        chunk_type = "curriculum"
                    elif any(word in content for word in ["principal", "director", "chairman", "board"]):
                        chunk_type = "administration"
                    elif any(word in content for word in ["eligibility", "admission", "entrance"]):
                        chunk_type = "admission"
                    elif any(word in content for word in ["career", "job", "prospects"]):
                        chunk_type = "career"
                    elif "course" in content and "|" in content:
                        chunk_type = "course_table"
                    
                    text.metadata.update({
                        "program": program,
                        "source": filename,
                        "chunk_id": i,
                        "chunk_type": chunk_type,
                        "content_preview": text.page_content[:100].replace('\n', ' ')
                    })
                
                all_texts.extend(texts)
                print(f"Processed {filename}: {len(texts)} chunks")
                
                if len(texts) > 0:
                    print(f"Sample chunk types: {set([t.metadata.get('chunk_type') for t in texts[:5]])}")
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    return all_texts

def create_vector_store(texts):
    print("Initializing embedding model...")
    
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={
            'normalize_embeddings': True,
            'batch_size': 32
        }
    )
    
    print("Creating vector database...")
    
    import shutil
    if os.path.exists("db"):
        shutil.rmtree("db")
        print("Removed existing database")
    
    vectordb = Chroma.from_documents(
        documents=texts,
        embedding=embedding,
        persist_directory="db",
        collection_metadata={
            "hnsw:space": "cosine",
            "description": "Enhanced Samriddhi College information database"
        }
    )
    
    print("Vector database created successfully!")
    
    print("Testing database retrieval...")
    test_queries = [
        "principal of samriddhi college",
        "CSIT semester 1 courses",
        "BCA eligibility criteria"
    ]
    
    for query in test_queries:
        try:
            results = vectordb.similarity_search(query, k=3)
            print(f"Query: '{query}' → Found {len(results)} results")
            if results:
                print(f"Top result preview: {results[0].page_content[:80]}...")
        except Exception as e:
            print(f"Query: '{query}' → Error: {e}")
    
    return vectordb

def analyze_database_content(vectordb):
    print("Database Content Analysis:")
    
    try:
        all_docs = vectordb.get()
        
        if 'metadatas' in all_docs:
            programs = {}
            chunk_types = {}
            
            for metadata in all_docs['metadatas']:
                prog = metadata.get('program', 'unknown')
                ctype = metadata.get('chunk_type', 'unknown')
                
                programs[prog] = programs.get(prog, 0) + 1
                chunk_types[ctype] = chunk_types.get(ctype, 0) + 1
            
            print(f"Programs: {dict(programs)}")
            print(f"Chunk Types: {dict(chunk_types)}")
            print(f"Total Documents: {len(all_docs.get('metadatas', []))}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 ENHANCED DATABASE CREATION PROCESS")
    print("="*60)
    
    # ✅ STEP 1: Download files from Supabase FIRST
    print("\n" + "="*60)
    print("STEP 1: Downloading from Supabase Storage")
    print("="*60)
    files_count = download_files_from_supabase()
    
    if files_count == 0:
        print("\n❌ No files downloaded. Exiting.")
        print("Please check:")
        print("  1. SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env")
        print("  2. Files uploaded to 'college-documents' bucket")
        exit(1)
    
    # ✅ STEP 2: Process downloaded files
    print("\n" + "="*60)
    print("STEP 2: Processing Documents")
    print("="*60)
    texts = load_and_process_md_files()
    
    if not texts:
        print("❌ No content was processed. Please check your .md files.")
        exit(1)
    
    print(f"✅ Successfully processed {len(texts)} text chunks")
    
    # ✅ STEP 3: Create vector database
    print("\n" + "="*60)
    print("STEP 3: Creating Vector Database")
    print("="*60)
    db = create_vector_store(texts)
    analyze_database_content(db)
    
    # ✅ STEP 4: Optional cleanup
    print("\n" + "="*60)
    print("STEP 4: Cleanup")
    print("="*60)
    try:
        cleanup = input("Delete temporary data/ folder? (y/n): ").lower()
        if cleanup == 'y':
            import shutil
            shutil.rmtree("data")
            print("🧹 Cleaned up temporary files")
        else:
            print("📁 Kept data/ folder for reference")
    except:
        print("📁 Kept data/ folder")
    
    print("\n" + "="*60)
    print("✅ DATABASE CREATION COMPLETED!")
    print(f"📍 Database location: {os.path.abspath('db')}")
    print("="*60)