from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

def load_and_process_md_files(directory="data"):
    """Enhanced processing with better chunking strategies"""
    all_texts = []
    
    # Enhanced program configuration
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
                
                # Enhanced separators
                base_separators = config["separators"].copy()
                
                # Add dynamic semester and section separators
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
                
                # Enhanced metadata
                for i, text in enumerate(texts):
                    content = text.page_content.lower()
                    
                    # Determine chunk type
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
                print(f"✅ Processed {filename}: {len(texts)} chunks")
                
                # Debug: Show some chunk previews
                if len(texts) > 0:
                    print(f"   Sample chunk types: {set([t.metadata.get('chunk_type') for t in texts[:5]])}")
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
    
    return all_texts

def create_vector_store(texts):
    """Create enhanced vector database with better configuration"""
    print("🔧 Initializing embedding model...")
    
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={
            'normalize_embeddings': True,
            'batch_size': 32
        }
    )
    
    print("📦 Creating vector database...")
    
    # Remove existing database
    import shutil
    if os.path.exists("db"):
        shutil.rmtree("db")
        print("🗑️  Removed existing database")
    
    # Create new database with enhanced settings
    vectordb = Chroma.from_documents(
        documents=texts,
        embedding=embedding,
        persist_directory="db",
        collection_metadata={
            "hnsw:space": "cosine",
            "description": "Enhanced Samriddhi College information database"
        }
    )
    
    print("💾 Vector database created successfully!")
    
    # Test the database
    print("\n🧪 Testing database retrieval...")
    test_queries = [
        "principal of samriddhi college",
        "CSIT semester 1 courses",
        "BCA eligibility criteria"
    ]
    
    for query in test_queries:
        try:
            results = vectordb.similarity_search(query, k=3)
            print(f"   Query: '{query}' → Found {len(results)} results")
            if results:
                print(f"      Top result preview: {results[0].page_content[:80]}...")
        except Exception as e:
            print(f"   Query: '{query}' → Error: {e}")
    
    return vectordb

def analyze_database_content(vectordb):
    """Analyze what's in the database for debugging"""
    print("\n📊 Database Content Analysis:")
    
    try:
        # Get all documents (sample)
        all_docs = vectordb.get()
        
        if 'metadatas' in all_docs:
            programs = {}
            chunk_types = {}
            
            for metadata in all_docs['metadatas']:
                prog = metadata.get('program', 'unknown')
                ctype = metadata.get('chunk_type', 'unknown')
                
                programs[prog] = programs.get(prog, 0) + 1
                chunk_types[ctype] = chunk_types.get(ctype, 0) + 1
            
            print(f"📁 Programs: {dict(programs)}")
            print(f"🏷️  Chunk Types: {dict(chunk_types)}")
            print(f"📄 Total Documents: {len(all_docs.get('metadatas', []))}")
        
    except Exception as e:
        print(f"   Analysis failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Database Creation Process")
    print("=" * 60)
    
    # Check if data directory exists
    if not os.path.exists("data"):
      
        exit(1)
    
    # Check for .md files
    md_files = [f for f in os.listdir("data") if f.endswith('.md')]
    if not md_files:
        print("❌ No .md files found in 'data' directory!")
        print("Please add your markdown files (Samriddhi.md, CSIT.md, etc.) to the 'data' directory.")
        exit(1)
    
    print(f"📋 Found {len(md_files)} markdown files: {md_files}")
    print("\n🔄 Processing documents...")
    
    texts = load_and_process_md_files()
    
    if not texts:
        print("❌ No content was processed. Please check your .md files.")
        exit(1)
    
    print(f"\n✅ Successfully processed {len(texts)} text chunks")
    
    db = create_vector_store(texts)
    analyze_database_content(db)
    
    print("\n" + "=" * 60)
    print("🎉 Database creation completed successfully!")
    print(f"📂 Database location: {os.path.abspath('db')}")
    print("✨ You can now run the query system!")
    print("=" * 60)