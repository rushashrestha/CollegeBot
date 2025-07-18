from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import shutil

def create_markdown_vector_db():
    try:
        print("🔄 Loading Markdown files...")
        loader_csit = UnstructuredMarkdownLoader("data/csit.md", mode="elements", strategy="fast")
        loader_bca = UnstructuredMarkdownLoader("data/bca.md", mode="elements", strategy="fast")
        
        # Load and combine documents
        documents = loader_csit.load() + loader_bca.load()
        print(f"✅ Loaded {len(documents)} documents")

        # ✅ Filter out complex metadata
        documents = [filter_complex_metadata(doc) for doc in documents]

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n## ", "\n### ", "\n• ", "\n- ", "\n|", "Course Code:"]
        )
        texts = text_splitter.split_documents(documents)
        print(f"📊 Split into {len(texts)} chunks")

        # Initialize embeddings
        embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        # Remove existing vector store if exists
        if os.path.exists("db"):
            shutil.rmtree("db")

        # Create vector DB
        vectordb = Chroma.from_documents(
            documents=texts,
            embedding=embedding,
            persist_directory="db"
        )
        vectordb.persist()
        print("🎉 Database created successfully!")
        return vectordb

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    create_markdown_vector_db()
