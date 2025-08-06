
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="College Chatbot API",
    summary="FastAPI backend for our college chatbot project using LLM"
)

# Enable CORS so frontend (Next.js or anything else) can access it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    
    return {"message": "College chatbot backend is running"}


