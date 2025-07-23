import { useState, useEffect } from 'react'; // Added useEffect import
import Loader from "./Components/Loader/Loader";
import './App.css';

function App() {
  const [showLoader, setShowLoader] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    { text: 'Ask me anything.', sender: 'bot' }
  ]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowLoader(false);
    }, 2000);

    return () => clearTimeout(timer);
  }, []); // Added dependency array

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

  return (
    <div className={`app-container ${darkMode ? 'dark' : 'light'}`}>
      <div className="header">
        <h1>Samriddhi-ChatBot</h1>
        <div className="auth-buttons">
          <button className="login-btn">Login</button>
          <button className="signup-btn">Sign Up</button>
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
              {msg.text}
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

export default App;