from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import shutil

# Load Markdown file
loader = TextLoader("data/BSW.md")
documents = loader.load()

# Text splitting configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n## ", "\n### ", "\n• ", "\n- ", "\n|", "Course Code:"]
)

# Split text into chunks
texts = text_splitter.split_documents(documents)
print(f"📊 Split into {len(texts)} chunks")

# Add metadata
for i, text in enumerate(texts):
    text.metadata['page'] = i // 3 + 1  # Simple pagination

# Remove existing vector store if exists
if os.path.exists("db"):
    shutil.rmtree("db")

# Instantiate the embedding model properly
embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# Store vectors in local 'db' directory (will be created automatically)
vectordb = Chroma.from_documents(
    texts,
    embedding,
    persist_directory="db",
    collection_metadata={"hnsw:space": "cosine"}
)
vectordb.persist()
