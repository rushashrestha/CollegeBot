from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter

# Load markdown file
loader = UnstructuredMarkdownLoader("data/CSIT.md")
documents = loader.load()

# Configure markdown splitting
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)

# Split documents
docs = markdown_splitter.split_text(documents[0].page_content)

# Add metadata
for i, doc in enumerate(docs):
    doc.metadata.update({
        "source": "CSIT.md",
        "chunk_id": i,
        "title": next((v for k, v in doc.metadata.items() if "Header" in k), "General Info")
    })

# Create vectorstore
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma.from_documents(
    docs,
    embedding,
    persist_directory="db",
    collection_metadata={"hnsw:space": "cosine"}
)
vectordb.persist()

print("Database created successfully!")