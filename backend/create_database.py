from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# Load Markdown file directly from data/BSW.md
loader = TextLoader("data/BSW.md")
documents = loader.load()

# Text splitting configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", "====", "•", "|", "Course Code"]
)

texts = text_splitter.split_documents(documents)

# Add metadata
for i, text in enumerate(texts):
    text.metadata['page'] = i//3 + 1  # Simple pagination

embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Store vectors in local 'db' directory (will be created automatically)
vectordb = Chroma.from_documents(
    texts, 
    embedding, 
    persist_directory="db",
    collection_metadata={"hnsw:space": "cosine"}
)
vectordb.persist()
