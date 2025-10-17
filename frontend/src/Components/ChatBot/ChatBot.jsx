import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  getCurrentUser, 
  logoutUser, 
  getCurrentUserWithRole,
  createChatSession,
  saveChatMessage,
  getUserChatSessions,
  getChatMessages,
  updateChatSessionTitle,
  deleteChatSession
} from '../../utils/auth';
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
  const [userInfo, setUserInfo] = useState({ name: 'Guest', email: '-', role: 'guest' });
  const [userRole, setUserRole] = useState('guest');
  const [userData, setUserData] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [messages, setMessages] = useState([
    { text: 'Hello! Welcome to Samriddhi ChatBot. Ask me anything.', sender: 'bot' }
  ]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Speech Recognition States
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [transcript, setTranscript] = useState('');
  
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize user info and speech recognition
  useEffect(() => {
    const initializeUser = async () => {
      try {
        const userWithRole = await getCurrentUserWithRole();
        const userRole = localStorage.getItem('userRole');
        const userEmail = localStorage.getItem('userEmail') || localStorage.getItem('adminEmail');
        
        if (userWithRole || userRole) {
          const role = userWithRole?.role || userRole || 'guest';
          setUserRole(role);
          setUserInfo({
            name: role === 'admin' ? 'Admin' : (userWithRole?.email ? userWithRole.email.split('@')[0] : 'User'),
            email: userWithRole?.email || userEmail || '-',
            role: role
          });
          
          // Fetch user data if logged in
          if (role !== 'guest' && userWithRole?.email) {
            await fetchUserData(userWithRole.email, role);
          }

          // Load chat history if user is authenticated
          if (userWithRole?.id) {
            await loadChatHistory(userWithRole.id);
          }
        }
      } catch (error) {
        console.error('Error fetching user:', error);
        // Fallback to localStorage
        const userRole = localStorage.getItem('userRole');
        const userEmail = localStorage.getItem('userEmail') || localStorage.getItem('adminEmail');
        if (userRole) {
          setUserRole(userRole);
          setUserInfo({
            name: userRole === 'admin' ? 'Admin' : 'User',
            email: userEmail || '-',
            role: userRole
          });
        }
      } finally {
        setShowLoader(false);
      }
    };

    initializeUser();

    // Speech Recognition initialization
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

  // Function to fetch user data
  const fetchUserData = async (email, role) => {
    try {
      let tableName = '';
      if (role === 'student') {
        tableName = 'students_data';
      } else if (role === 'teacher') {
        tableName = 'teachers_data';
      } else if (role === 'admin') {
        tableName = 'admin_users';
      }
      
      if (tableName) {
        const response = await fetch(`http://localhost:5000/api/user-data`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, table: tableName }),
        });
        
        if (response.ok) {
          const data = await response.json();
          setUserData(data.user_data);
        }
      }
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  };

  // Function to load chat history
  const loadChatHistory = async (userId) => {
    try {
      setLoadingHistory(true);
      const { data, error } = await getUserChatSessions(userId);
      
      if (error) throw error;
      
      if (data) {
        const formattedSessions = data.map(session => ({
          id: session.id,
          title: session.title,
          timestamp: new Date(session.updated_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          }),
          rawDate: new Date(session.updated_at)
        }));
        
        setChatHistory(formattedSessions);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Function to load a specific chat session
  const loadChatSession = async (sessionId) => {
    try {
      const { data, error } = await getChatMessages(sessionId);
      
      if (error) throw error;
      
      if (data) {
        const formattedMessages = data.map(msg => ({
          text: msg.message_text,
          sender: msg.sender,
          timestamp: new Date(msg.created_at)
        }));
        
        setMessages(formattedMessages);
        setCurrentSessionId(sessionId);
        setSidebarOpen(false);
      }
    } catch (error) {
      console.error('Error loading chat session:', error);
    }
  };

  // Auto-create session on first message if needed
  useEffect(() => {
    const initializeSession = async () => {
      if (messages.length > 1 && !currentSessionId) {
        await handleNewChat();
      }
    };
    
    initializeSession();
  }, [messages.length]);

  // Auto-scroll to bottom when new messages are added
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
    
    let sessionCreated = false;
    let newSessionId = null;
    
    // Create new session if this is the first message
    if (!currentSessionId) {
      const user = await getCurrentUser();
      if (user) {
        try {
          console.log('Creating session with query:', query);
          
          // Use auto-title generation for new sessions
          const { data: sessionData, error } = await createChatSessionWithAutoTitle(
            user.email,
            userRole,
            query, // First message used for title generation
            user.id
          );
          
          if (sessionData && !error) {
            newSessionId = sessionData.id;
            setCurrentSessionId(sessionData.id);
            console.log('Auto-generated title:', sessionData.title);
            
            // Add to chat history
            setChatHistory(prev => [{
              id: sessionData.id,
              title: sessionData.title,
              timestamp: 'Now',
              rawDate: new Date(sessionData.created_at)
            }, ...prev]);
            sessionCreated = true;
          } else {
            console.error('Auto-title failed, using fallback');
            // Fallback: create session with default title
            const { data: fallbackSession, error: fallbackError } = await createChatSession(
              user.email,
              userRole,
              `Chat ${new Date().toLocaleTimeString()}`,
              user.id
            );
            if (fallbackSession && !fallbackError) {
              setCurrentSessionId(fallbackSession.id);
              setChatHistory(prev => [{
                id: fallbackSession.id,
                title: fallbackSession.title,
                timestamp: 'Now',
                rawDate: new Date(fallbackSession.created_at)
              }, ...prev]);
              sessionCreated = true;
            }
          }
        } catch (error) {
          console.error('Error creating chat session:', error);
          // Guest user or error - create local session
          setCurrentSessionId(`local-${Date.now()}`);
        }
      } else {
        // Guest user - create local session
        setCurrentSessionId(`guest-${Date.now()}`);
      }
    }
    
    // Save user message to database if we have a session (and it's not a local/guest session)
    if (currentSessionId && !currentSessionId.startsWith('local-') && !currentSessionId.startsWith('guest-')) {
      await saveChatMessage(currentSessionId, query, 'user');
    }
    
    setQuery('');
    
    try {
      const response = await fetch('http://localhost:5000/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: query,
          user_role: userRole,
          user_data: userData 
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Backend suggested title:', data.suggested_title);
      
      // Add bot response
      const botMessage = { 
        text: data.response,
        sender: 'bot',
        access_restricted: data.access_restricted 
      };
      
      setMessages(prev => [...prev, botMessage]);
      
      // Save bot message to database (if not local/guest session)
      if (currentSessionId && !currentSessionId.startsWith('local-') && !currentSessionId.startsWith('guest-')) {
        await saveChatMessage(currentSessionId, data.response, 'bot');
        
        // Only update title if backend provides a BETTER title (not generic)
        if (sessionCreated && data.suggested_title && !isGenericTitle(data.suggested_title)) {
          console.log('Updating to better title:', data.suggested_title);
          await updateChatSessionTitle(currentSessionId, data.suggested_title);
          // Update local chat history
          setChatHistory(prev => prev.map(chat => 
            chat.id === currentSessionId 
              ? { ...chat, title: data.suggested_title }
              : chat
          ));
        } else if (sessionCreated) {
          console.log('Keeping auto-generated title, backend title is generic');
        }
      }
      
    } catch (error) {
      console.error('Fetch error:', error);
      const errorMessage = { 
        text: "Sorry, I couldn't get a response from the server.", 
        sender: 'bot' 
      };
      setMessages(prev => [...prev, errorMessage]);
      
      // Save error message to database (if not local/guest session)
      if (currentSessionId && !currentSessionId.startsWith('local-') && !currentSessionId.startsWith('guest-')) {
        await saveChatMessage(currentSessionId, errorMessage.text, 'bot');
      }
    }
  }
};

// Add this helper function to detect generic titles
const isGenericTitle = (title) => {
  const genericTitles = ['chat', 'new chat', 'conversation', 'discussion', 'query'];
  return genericTitles.includes(title.toLowerCase());
};

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
      // Clear localStorage
      localStorage.removeItem('userRole');
      localStorage.removeItem('userEmail');
      localStorage.removeItem('adminEmail');
      localStorage.removeItem('isAuthenticated');
      localStorage.removeItem('supabase_user_id');
      
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      // Fallback: clear localStorage and redirect
      localStorage.clear();
      navigate('/login');
    }
  };

  const handleNewChat = async () => {
    const user = await getCurrentUser();
    
    if (user) {
      try {
        // Create new session in database
        const title = `Chat ${new Date().toLocaleTimeString()}`;
        const { data, error } = await createChatSession(
          user.email, 
          userRole, 
          title, 
          user.id
        );
        
        if (error) throw error;
        
        if (data) {
          setCurrentSessionId(data.id);
          // Add to chat history
          setChatHistory(prev => [{
            id: data.id,
            title: data.title,
            timestamp: 'Now',
            rawDate: new Date(data.created_at)
          }, ...prev]);
        }
      } catch (error) {
        console.error('Error creating new chat session:', error);
        // Fallback: create local session without saving to DB
        setCurrentSessionId(`local-${Date.now()}`);
      }
    } else {
      // Guest user - create local session
      setCurrentSessionId(`guest-${Date.now()}`);
    }
    
    // Clear messages and close sidebar
    setMessages([
      { text: 'Hello! Welcome to Samriddhi ChatBot. Ask me anything.', sender: 'bot' }
    ]);
    setSidebarOpen(false);
    
    // Stop any ongoing speech recognition
    if (isListening) {
      stopListening();
    }
  };

  // Function to delete a chat session
  const handleDeleteChat = async (sessionId, e) => {
    e.stopPropagation(); // Prevent loading the chat
    
    try {
      const { error } = await deleteChatSession(sessionId);
      
      if (error) throw error;
      
      // Remove from local state
      setChatHistory(prev => prev.filter(chat => chat.id !== sessionId));
      
      // If current session is deleted, clear it
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([
          { text: 'Hello! Welcome to Samriddhi ChatBot. Ask me anything.', sender: 'bot' }
        ]);
      }
    } catch (error) {
      console.error('Error deleting chat session:', error);
    }
  };

  // Show loader if showLoader is true
  if (showLoader) {
    return <Loader />;
  }

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
          {loadingHistory ? (
            <div className="loading-history">Loading...</div>
          ) : chatHistory.length === 0 ? (
            <div className="no-chats">No previous chats</div>
          ) : (
            chatHistory.map(chat => (
              <div 
                key={chat.id} 
                className={`chat-history-item ${currentSessionId === chat.id ? 'active' : ''}`}
                onClick={() => loadChatSession(chat.id)}
              >
                <div className="chat-title">{chat.title}</div>
                <div className="chat-timestamp">{chat.timestamp}</div>
                <button 
                  className="delete-chat-btn"
                  onClick={(e) => handleDeleteChat(chat.id, e)}
                  title="Delete chat"
                >
                  ×
                </button>
              </div>
            ))
          )}
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
                <div className="username">{userInfo.name}</div>
                <div className="email">{userInfo.email}</div>
                <div className="user-role">Role: {userInfo.role}</div>
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
            <div className="role-indicator">
              
              
            </div>
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
                {msg.access_restricted && (
                  <div className="access-warning">
                    Access Restricted
                  </div>
                )}
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