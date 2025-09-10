import os
import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# ==============================
# PDF Processing
# ==============================
def process_pdf(pdf_path, persist_dir):
    # Load PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    # Text splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "====", "•", "|", "Course Code"]
    )

    texts = text_splitter.split_documents(documents)

    # Add page numbers metadata
    for i, text in enumerate(texts):
        text.metadata['page'] = text.metadata.get('page', i // 3 + 1)

    # Create vector DB
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = Chroma.from_documents(
        texts,
        embedding,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )
    vectordb.persist()
    print(f"✅ PDF data stored in {persist_dir}")
    return vectordb


# ==============================
# CSV Processing
# ==============================
def process_csv(csv_path, persist_dir):
    # Read CSV
    df = pd.read_csv(csv_path)

    docs = []
    for _, row in df.iterrows():
        text = (
            f"Student ID: {row['ID']}, Name: {row['Name']}, "
            f"DOB (AD): {row['DOB (A.D.)']}, DOB (BS): {row['DOB (B.S.)']}, "
            f"Gender: {row['Gender']}, Phone: {row['Phone']}, Email: {row['Email']}, "
            f"Permanent Address: {row['Perm. Address']}, Temporary Address: {row['Temp. Address']}, "
            f"Program: {row['Program']}, Batch: {row['Batch']}, Section: {row['Section']}, "
            f"Year/Semester: {row['Year/Semester']}, Roll No.: {row['Roll No.']}, "
            f"Symbol No.: {row['Symbol No.']}, Registration No.: {row['Registration No.']}, "
            f"Joined Date: {row['Joined Date']}"
        )

        docs.append(Document(
            page_content=text,
            metadata={"id": row["ID"], "name": row["Name"]}
        ))

    # Create vector DB
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = Chroma.from_documents(
        docs,
        embedding,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )
    vectordb.persist()
    print(f"✅ Student CSV data stored in {persist_dir}")
    return vectordb


# ==============================
# Run both
# ==============================
if __name__ == "__main__":
    # Paths
    pdf_path = "data/scraped_pdfs/full_csit_program.pdf"
    pdf_db_dir = "db/pdf"

    csv_path = "data/csv/StudentDetails.csv"
    student_db_dir = "db/student"

    # Create vector DBs
    if os.path.exists(pdf_path):
        process_pdf(pdf_path, pdf_db_dir)
    else:
        print("⚠️ PDF file not found, skipping PDF processing.")

    if os.path.exists(csv_path):
        process_csv(csv_path, student_db_dir)
    else:
        print("⚠️ CSV file not found, skipping Student DB processing.")
