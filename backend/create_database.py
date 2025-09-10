import os
import pandas as pd
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# ==============================
# Markdown Processing
# ==============================
def process_md_files(md_dir, persist_dir):
    docs = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "====", "•", "|"]
    )

    for file in os.listdir(md_dir):
        if file.endswith(".md"):
            loader = TextLoader(os.path.join(md_dir, file), encoding="utf-8")
            documents = loader.load()
            splits = text_splitter.split_documents(documents)
            docs.extend(splits)

    if not docs:
        print("⚠️ No Markdown files found.")
        return None

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
    print(f"✅ Markdown data stored in {persist_dir}")
    return vectordb


# ==============================
# CSV Processing
# ==============================
def process_csv(csv_path, persist_dir):
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

    if not docs:
        print("⚠️ No student records found.")
        return None

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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    md_dir = os.path.join(BASE_DIR, "data")  # where BBS.md, bca.md, etc. are
    md_db_dir = os.path.join(BASE_DIR, "db/md")

    csv_path = os.path.join(BASE_DIR, "data", "csv", "StudentsDetails.csv")
    student_db_dir = os.path.join(BASE_DIR, "db/student")

    # Create vector DBs
    process_md_files(md_dir, md_db_dir)

    if os.path.exists(csv_path):
        process_csv(csv_path, student_db_dir)
    else:
        print("⚠️ CSV file not found, skipping Student DB processing.")
