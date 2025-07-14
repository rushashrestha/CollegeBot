from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# Enhanced PDF processing
loader = PyPDFLoader("data/CSIT.pdf")
documents = loader.load()

# Improved text splitting
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", "====", "•", "|", "Course Code"]
)

texts = text_splitter.split_documents(documents)

# Add page numbers to metadata
for i, text in enumerate(texts):
    text.metadata['page'] = text.metadata.get('page', i//3 + 1)  # Group every 3 chunks

embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Create vectorstore with enhanced metadata
vectordb = Chroma.from_documents(
    texts, 
    embedding, 
    persist_directory="db",
    collection_metadata={"hnsw:space": "cosine"}  # Better similarity metric
)
vectordb.persist()