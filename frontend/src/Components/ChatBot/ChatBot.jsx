import { useState, useEffect, useRef } from 'react';
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
const CourseTable = ({ courses }) => (
  <div className="course-table-container">
    {/* <h3>CSIT {semester} Semester Courses</h3> */}
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    { id: 1, title: 'CSIT Course Information', timestamp: 'Today' },
    { id: 2, title: 'Previous Conversation', timestamp: 'Yesterday' },
    { id: 3, title: 'General Questions', timestamp: '2 days ago' }
  ]);
  const [messages, setMessages] = useState([
    { text: 'Hello! Welcome to Samriddhi ChatBot. Ask me anything.', sender: 'bot' }
  ]);
  
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages are added
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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

  const handleNewChat = () => {
    setMessages([
      { text: 'Hello! Welcome to Samriddhi ChatBot. Ask me anything.', sender: 'bot' }
    ]);
    setSidebarOpen(false);
  };

  return (
    <div className={`app-container ${darkMode ? 'dark' : 'light'}`}>
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            New chat
          </button>
        </div>
        
        <div className="chat-history">
          <h3>Recent Chats</h3>
          {chatHistory.map(chat => (
            <div key={chat.id} className="chat-history-item">
              <div className="chat-title">{chat.title}</div>
              <div className="chat-timestamp">{chat.timestamp}</div>
            </div>
          ))}
        </div>
        
        {/* Profile Section */}
        <div className="profile-section">
          <div className="profile-trigger" onClick={() => setProfileOpen(!profileOpen)}>
            <div className="profile-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span>My Profile</span>
            <svg className={`chevron ${profileOpen ? 'up' : 'down'}`} width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M18 15L12 9L6 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          
          {profileOpen && (
            <div className="profile-dropdown">
              <div className="profile-info">
                <div className="username">Guest</div>
                <div className="email">-</div>
              </div>
              <button className="logout-btn" onClick={handleLogout}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="16,17 21,12 16,7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="21" y1="12" x2="9" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Sidebar Overlay */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      
      {/* Main Content */}
      <div className="main-content">
        {/* Header */}
        <div className="header">
          <div className="header-left">
            <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <h1>AskSamriddhi</h1>
          </div>
          
          <div className="header-right">
            <button 
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
              title={`Switch to ${darkMode ? 'light' : 'dark'} mode`}
            >
              {darkMode ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2"/>
                  <line x1="12" y1="1" x2="12" y2="3" stroke="currentColor" strokeWidth="2"/>
                  <line x1="12" y1="21" x2="12" y2="23" stroke="currentColor" strokeWidth="2"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="currentColor" strokeWidth="2"/>
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="currentColor" strokeWidth="2"/>
                  <line x1="1" y1="12" x2="3" y2="12" stroke="currentColor" strokeWidth="2"/>
                  <line x1="21" y1="12" x2="23" y2="12" stroke="currentColor" strokeWidth="2"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="currentColor" strokeWidth="2"/>
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="currentColor" strokeWidth="2"/>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" stroke="currentColor" strokeWidth="2"/>
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Chat Container */}
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
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Container */}
        <div className="input-container">
          <div className="input-wrapper">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your question..."
            />
            <button className="send-btn" onClick={handleSend} disabled={!query.trim()}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatBot;