import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Loader from "../Loader/Loader";
import './ChatBot.css';

// Function to detect if response contains course/table data
const detectCourseContent = (text) => {
  const courseKeywords = ['course', 'semester', 'credit', 'subject', 'syllabus', 'curriculum'];
  const hasTableStructure = text.includes('•') || text.includes('*') || text.includes('-');
  const lowerText = text.toLowerCase();
  
  return courseKeywords.some(keyword => lowerText.includes(keyword)) && hasTableStructure;
};

// Function to parse course content into structured data
const parseCourseContent = (text) => {
  const lines = text.split('\n').filter(line => line.trim());
  const courses = [];
  
  lines.forEach(line => {
    // Match patterns like "3 (Code: Theory of Computation)" or "• 3 (Code: Theory of Computation)"
    const match = line.match(/[•*-]?\s*(\d+)\s*\([^:]*:\s*([^)]+)\)/);
    if (match) {
      courses.push({
        credits: match[1],
        title: match[2].trim()
      });
    }
  });
  
  return courses;
};

// Component to render course table
const CourseTable = ({ courses, semester }) => (
  <div className="course-table-container">
    <h3>CSIT {semester} Semester Courses</h3>
    <table className="course-table">
      <thead>
        <tr>
          <th>Course Title</th>
          <th>Credit Hours</th>
        </tr>
      </thead>
      <tbody>
        {courses.map((course, index) => (
          <tr key={index}>
            <td>{course.title}</td>
            <td>{course.credits}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// Component to render formatted message
const FormattedMessage = ({ text }) => {
  // Check if it's course content
  if (detectCourseContent(text)) {
    const courses = parseCourseContent(text);
    const semesterMatch = text.match(/(\w+)\s+semester/i);
    const semester = semesterMatch ? semesterMatch[1] : '';
    
    if (courses.length > 0) {
      return <CourseTable courses={courses} semester={semester} />;
    }
  }
  
  // For regular text, convert basic markdown-like formatting
  const formatText = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
      .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
      .replace(/^[•*-]\s+(.+)$/gm, '<li>$1</li>') // List items
      .replace(/\n/g, '<br/>'); // Line breaks
  };
  
  return (
    <div 
      className="formatted-message" 
      dangerouslySetInnerHTML={{ __html: formatText(text) }}
    />
  );
};

function ChatBot() {
  const [showLoader, setShowLoader] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    { text: 'Hello! Welcome to Samriddhi ChatBot. Ask me anything.', sender: 'bot' }
  ]);
  
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowLoader(false);
    }, 2000);

    return () => clearTimeout(timer);
  }, []);

  // Show loader if showLoader is true
  if (showLoader) {
    return <Loader />;
  }

  const handleSend = async () => {
    if (query.trim()) {
      // Add user message immediately
      const userMessage = { text: query, sender: 'user' };
      setMessages(prev => [...prev, userMessage]);
      setQuery('');
      
      try {
        const response = await fetch('http://localhost:5000/api/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query: query }),
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add bot response
        setMessages(prev => [...prev, { 
          text: data.response,
          sender: 'bot' 
        }]);
      } catch (error) {
        console.error('Fetch error:', error);
        setMessages(prev => [...prev, { 
          text: "Sorry, I couldn't get a response from the server.", 
          sender: 'bot' 
        }]);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const handleLogout = () => {
    navigate('/login');
  };

  return (
    <div className={`app-container ${darkMode ? 'dark' : 'light'}`}>
      <div className="header">
        <h1>Samriddhi-ChatBot</h1>
        <div className="auth-buttons">
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
          <button 
            className="theme-btn"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>
      </div>

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              {msg.sender === 'bot' ? (
                <FormattedMessage text={msg.text} />
              ) : (
                msg.text
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="input-container">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your question..."
        />
        <button className="send-btn" onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatBot;