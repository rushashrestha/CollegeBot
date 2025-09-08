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
  if (detectCourseContent(text)) {
    const courses = parseCourseContent(text);
    const semesterMatch = text.match(/(\w+)\s+semester/i);
    const semester = semesterMatch ? semesterMatch[1] : '';
    
    if (courses.length > 0) {
      return <CourseTable courses={courses} semester={semester} />;
    }
  }
  
  const formatText = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^[•*-]\s+(.+)$/gm, '<li>$1</li>')
      .replace(/\n/g, '<br/>');
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

  // Speech Recognition States
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [transcript, setTranscript] = useState('');
  
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize Speech Recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      setSpeechSupported(true);
      
      const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        setTranscript(interimTranscript);
        
        if (finalTranscript) {
          setQuery(finalTranscript);
          setTranscript('');
        }
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        setTranscript('');
      };

      recognition.onend = () => {
        setIsListening(false);
        setTranscript('');
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

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

  // Speech Recognition Functions
  const startListening = () => {
    if (recognitionRef.current && speechSupported) {
      setQuery(''); // Clear existing text
      recognitionRef.current.start();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const handleSend = async () => {
    if (query.trim()) {
      // Stop listening if currently active
      if (isListening) {
        stopListening();
      }

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
    // Stop any ongoing speech recognition
    if (isListening) {
      stopListening();
    }
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

        {/* Input Container with Speech Recognition */}
        <div className="input-container">
          <div className="input-wrapper">
            <input
              type="text"
              value={transcript || query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isListening ? "Listening..." : "Type your question or click the mic to speak..."}
              className={transcript ? 'listening-input' : ''}
            />
            
            {/* Speech Recognition Button */}
            {speechSupported && (
              <button
                className={`mic-btn ${isListening ? 'listening' : ''}`}
                onClick={isListening ? stopListening : startListening}
                title={isListening ? "Stop listening" : "Start voice input"}
              >
                {isListening ? (
                  // Stop/Pause icon
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="6" y="4" width="4" height="16" rx="2" fill="currentColor"/>
                    <rect x="14" y="4" width="4" height="16" rx="2" fill="currentColor"/>
                  </svg>
                ) : (
                  // Microphone icon
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2C13.1046 2 14 2.89543 14 4V12C14 13.1046 13.1046 14 12 14C10.8954 14 10 13.1046 10 12V4C10 2.89543 10.8954 2 12 2Z" fill="currentColor"/>
                    <path d="M19 10V12C19 16.4183 15.4183 20 11 20H13C17.4183 20 21 16.4183 21 12V10H19Z" fill="currentColor"/>
                    <path d="M5 10V12C5 16.4183 8.58172 20 13 20H11C6.58172 20 3 16.4183 3 12V10H5Z" fill="currentColor"/>
                    <rect x="11" y="20" width="2" height="4" fill="currentColor"/>
                  </svg>
                )}
              </button>
            )}
            
            <button 
              className="send-btn" 
              onClick={handleSend} 
              disabled={!query.trim() && !transcript.trim()}
            >
              Send
            </button>
          </div>
          
          {/* Speech Recognition Status */}
          {isListening && (
            <div className="listening-status">
              <div className="pulse-dot" />
              Listening... Speak now
            </div>
          )}
          
          {!speechSupported && (
            <div className="speech-unsupported">
              Speech recognition not supported in this browser
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatBot;