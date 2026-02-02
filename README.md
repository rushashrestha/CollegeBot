# 🎓 CollegeBot - AI-Powered College Information Chatbot

A full-stack AI chatbot application that provides intelligent responses to queries about Samriddhi College programs, admissions, courses, and student information using LLMs and vector databases.

## Overview

CollegeBot is a comprehensive solution combining:
- **Backend**: FastAPI server with LLM integration (Groq, OpenAI)
- **Frontend**: React application with modern UI components
- **Database**: ChromaDB for vector embeddings and Supabase for user data
- **Testing**: Playwright end-to-end testing suite

## Features

- 🤖 **AI-Powered Responses**: Uses Groq and Langchain for intelligent answers
- 📚 **College Information**: Details about programs (BCA, CSIT, BSW, BBS), courses, and admissions
- 👥 **User Management**: Authentication via Supabase
- 📊 **Admin Dashboard**: Manage college data and user information
- 🔐 **Protected Routes**: Role-based access control

## Project Structure

```
CollegeBot/
├── backend/                    # Python FastAPI server
│   ├── main.py                # FastAPI app entry point
│   ├── server.py              # Additional server utilities
│   ├── query_llm.py           # LLM query logic
│   ├── create_database.py     # Database initialization
│   ├── fill.py                # Populate database with college data
│   ├── requirements.txt        # Python dependencies
│   └── data/                  # College information (markdown files)
│       ├── bca.md
│       ├── csit.md
│       ├── bsw.md
│       └── bbs.md
├── frontend/                   # React Vite application
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── main.jsx           # Entry point
│   │   ├── Components/
│   │   │   ├── ChatBot/       # Chatbot UI
│   │   │   ├── LoginSignup/   # Auth pages
│   │   │   ├── AdminDashboard/# Admin panel
│   │   │   └── Loader/        # Loading indicator
│   │   └── utils/
│   │       ├── auth.js        # Authentication utilities
│   │       ├── supabase.js    # Supabase client
│   │       └── ProtectedRoute.jsx
│   ├── package.json
│   └── vite.config.js
├── Testing/                    # E2E tests
│   ├── tests/
│   │   ├── LoginTest.spec.js
│   │   └── fixtures/
│   └── playwright.config.js
└── db/                         # Database storage
    └── chroma.sqlite3         # Vector database
```

## Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Navigate to backend:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the `backend/` directory:
   ```env
   SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_key
   GROQ_API_KEY=your_groq_api_key
   OPENAI_API_KEY=your_openai_api_key (optional)
   ```

5. **Create and populate the database:**
   ```bash
   python create_database.py
   python fill.py
   ```

### Frontend Setup

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   Create a `.env.local` file:
   ```env
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_key
   ```

   ```

   ```

## Running the Application

### Backend
```bash
cd backend
source venv/bin/activate  # Activate virtual environment
python main.py  # or: uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`

### Frontend
```bash
cd frontend
npm run dev
```
The frontend will be available at `http://localhost:5173` (or another port if 5173 is in use)

```

## Key Dependencies

### Backend
- **FastAPI**: Web framework
- **Langchain**: LLM orchestration
- **ChromaDB**: Vector database
- **Groq**: LLM provider
- **Supabase**: Authentication & database
- **Sentence-transformers**: Embeddings

### Frontend
- **React 19**: UI library
- **Vite**: Build tool
- **Material-UI (MUI)**: Component library
- **React Router**: Navigation
- **Supabase JS**: Auth & real-time data
- **React Hook Form**: Form management
- **Zod**: Schema validation

## API Endpoints

The backend FastAPI server exposes the following endpoints:

- `GET /` - Health check
- `POST /query` - Query the chatbot
- Additional endpoints for admin operations (defined in `main.py`)

## Environment Variables

### Backend
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `GROQ_API_KEY` | Groq API key for LLM |
| `OPENAI_API_KEY` | OpenAI API key (optional) |

### Frontend
| Variable | Description |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key |

## Usage Examples

### Interactive Chatbot (Backend)
Run the interactive chat directly:
```bash
python query_llm.py
```

This starts an interactive terminal interface where you can ask questions about the college.

### Query via API
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What programs does the college offer?"}'
```

## Database

The project uses **ChromaDB** for vector embeddings of college information. The database is stored locally at `db/chroma.sqlite3`.

To reinitialize the database:
```bash
cd backend
python create_database.py
python fill.py
```

## Authentication

The application uses **Supabase** for user authentication. Users can:
- Sign up with email
- Log in with credentials
- Access role-based features (student, teacher, admin)


```

## Features Overview

### ChatBot Page
- Interactive chat interface
- Real-time responses from AI
- Chat history management

### Admin Dashboard
- View and manage student information
- Add/edit college programs
- Monitor system analytics

### Login/Signup
- User registration
- Email/password authentication
- Secure session management

## Development

### Code Quality
- ESLint for frontend code linting
```bash
cd frontend
npm run lint
```

### Building for Production
**Frontend:**
```bash
cd frontend
npm run build
```

**Backend:** Use a production ASGI server like Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## Troubleshooting

### Missing Dependencies
If you encounter `ModuleNotFoundError`:
```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

### Database Errors
Reset ChromaDB:
```bash
cd backend
rm db/chroma.sqlite3
python create_database.py
python fill.py
```

### CORS Issues
Ensure backend CORS middleware is configured (already set in `main.py`)

## License

This project is proprietary and for Samriddhi College use.

## Support

For issues or questions, contact the development team or open an issue in the repository.

---

**Last Updated**: February 2, 2026
