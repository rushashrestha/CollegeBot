import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  getCurrentUser,
  logoutUser,
  getCurrentUserWithRole,
  createChatSession,
  saveChatMessage,
  getUserChatSessions,
  getChatMessages,
  updateChatSessionTitle,
  deleteChatSession,
} from "../../utils/auth";
import Loader from "../Loader/Loader";
import "./ChatBot.css";

// Function to detect if response contains course/table data
const detectCourseContent = (text) => {
  const courseKeywords = [
    "course",
    "semester",
    "credit",
    "subject",
    "syllabus",
    "curriculum",
  ];
  const hasTableStructure =
    text.includes("•") || text.includes("*") || text.includes("-");
  const lowerText = text.toLowerCase();

  return (
    courseKeywords.some((keyword) => lowerText.includes(keyword)) &&
    hasTableStructure
  );
};

// Function to parse course content into structured data
const parseCourseContent = (text) => {
  const lines = text.split("\n").filter((line) => line.trim());
  const courses = [];

  lines.forEach((line) => {
    const match = line.match(/[•*-]?\s*(\d+)\s*\([^:]*:\s*([^)]+)\)/);
    if (match) {
      courses.push({
        credits: match[1],
        title: match[2].trim(),
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
    const semester = semesterMatch ? semesterMatch[1] : "";

    if (courses.length > 0) {
      return <CourseTable courses={courses} semester={semester} />;
    }
  }

  const formatText = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/^[•*-]\s+(.+)$/gm, "<li>$1</li>")
      .replace(/\n/g, "<br/>");
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
  const [darkMode, setDarkMode] = useState(true);
  const [query, setQuery] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [userInfo, setUserInfo] = useState({
    name: "Guest",
    email: "-",
    role: "guest",
  });
  const [userRole, setUserRole] = useState("guest");
  const [userData, setUserData] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    return localStorage.getItem("currentSessionId") || null;
  });
  const [chatHistory, setChatHistory] = useState([]);
  const [messages, setMessages] = useState([
    {
      text: "Hello! Welcome to Samriddhi ChatBot. Ask me anything.",
      sender: "bot",
    },
  ]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isTyping, setIsTyping] = useState(false); // ✅ NEW: Loading state

  //  STATES FOR PASSWORD CHANGE
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // Speech Recognition States
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [transcript, setTranscript] = useState("");

  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize user info and speech recognition
  useEffect(() => {
    const initializeUser = async () => {
      console.log("=== CHATBOT INITIALIZATION START ===");
      console.log("🔄 INITIALIZING USER - localStorage contents:");
      console.log("   - userRole:", localStorage.getItem("userRole"));
      console.log("   - userEmail:", localStorage.getItem("userEmail"));
      console.log(
        "   - isAuthenticated:",
        localStorage.getItem("isAuthenticated")
      );
      console.log("   - userData:", localStorage.getItem("userData"));

      try {
        const storedRole = localStorage.getItem("userRole");
        const storedEmail =
          localStorage.getItem("userEmail") ||
          localStorage.getItem("adminEmail");
        const isAuthenticated = localStorage.getItem("isAuthenticated");

        console.log("📋 Using stored data:", {
          role: storedRole,
          email: storedEmail,
          authenticated: isAuthenticated,
        });

        if (
          isAuthenticated === "true" &&
          storedRole &&
          storedRole !== "guest"
        ) {
          console.log("✅ Using stored authenticated user:", storedRole);

          setUserRole(storedRole);
          setUserInfo({
            name: storedEmail
              ? storedEmail.split("@")[0]
              : storedRole.charAt(0).toUpperCase() + storedRole.slice(1),
            email: storedEmail || "-",
            role: storedRole,
          });

          if (storedRole !== "guest" && storedEmail) {
            await fetchUserData(storedEmail, storedRole);
          }

          try {
            const userWithRole = await getCurrentUserWithRole();
            if (userWithRole?.id) {
              await loadChatHistory(userWithRole.id);
            }
          } catch (historyError) {
            console.log(
              "ℹ️ Could not load chat history (expected for expired sessions)"
            );
          }
        } else {
          console.log("🎭 No valid authentication, starting as guest");
          setUserRole("guest");
          setUserInfo({
            name: "Guest",
            email: "-",
            role: "guest",
          });
        }
      } catch (error) {
        console.log("🔄 Fallback to guest mode due to error");
        setUserRole("guest");
        setUserInfo({
          name: "Guest",
          email: "-",
          role: "guest",
        });
      } finally {
        setShowLoader(false);
      }
    };

    initializeUser();

    // Speech Recognition initialization
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      setSpeechSupported(true);

      const SpeechRecognition =
        window.webkitSpeechRecognition || window.SpeechRecognition;
      const recognition = new SpeechRecognition();

      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let finalTranscript = "";
        let interimTranscript = "";

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
          setTranscript("");
        }
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
        setTranscript("");
      };

      recognition.onend = () => {
        setIsListening(false);
        setTranscript("");
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  useEffect(() => {
    const shouldShowModal = sessionStorage.getItem("show_password_modal");
    if (shouldShowModal === "true" && userRole !== "guest") {
      sessionStorage.removeItem("show_password_modal");
      setTimeout(() => {
        setShowChangePasswordModal(true);
      }, 1000);
    }
  }, [userRole]);

  // Function to fetch user data
  const fetchUserData = async (email, role) => {
    try {
      let tableName = "";
      if (role === "student") {
        tableName = "students_data";
      } else if (role === "teacher") {
        tableName = "teachers_data";
      } else if (role === "admin") {
        tableName = "admin_users";
      }

      if (tableName) {
        const response = await fetch(`http://localhost:5000/api/user-data`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email, table: tableName }),
        });

        if (response.ok) {
          const data = await response.json();
          setUserData(data.user_data);
        }
      }
    } catch (error) {
      console.error("Error fetching user data:", error);
    }
  };

  // Function to load chat history
  const loadChatHistory = async (userId) => {
    try {
      console.log("📚 Loading chat history for user:", userId);
      setLoadingHistory(true);

      const { data, error } = await getUserChatSessions(userId);

      if (error) {
        console.error("❌ Error loading chat sessions:", error);
        throw error;
      }

      console.log("✅ Chat sessions loaded:", data?.length || 0);

      if (data && data.length > 0) {
        const formattedSessions = data.map((session) => ({
          id: session.id,
          title: session.title,
          timestamp: new Date(session.updated_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }),
          rawDate: new Date(session.updated_at),
        }));

        console.log("📋 Formatted sessions:", formattedSessions);
        setChatHistory(formattedSessions);
      } else {
        console.log("ℹ️ No chat sessions found");
        setChatHistory([]);
      }
    } catch (error) {
      console.error("💥 Error loading chat history:", error);
      setChatHistory([]);
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
        const formattedMessages = data.map((msg) => ({
          text: msg.message_text,
          sender: msg.sender,
          timestamp: new Date(msg.created_at),
        }));

        setMessages(formattedMessages);
        setCurrentSessionId(sessionId);
        setSidebarOpen(false);
      }
    } catch (error) {
      console.error("Error loading chat session:", error);
    }
  };

  // Auto-scroll to bottom when new messages are added
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]); // ✅ Also scroll when typing state changes

  // Save current session ID to localStorage
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem("currentSessionId", currentSessionId);
    } else {
      localStorage.removeItem("currentSessionId");
    }
  }, [currentSessionId]);

  // Restore session messages on reload
  useEffect(() => {
    const restoreSession = async () => {
      if (currentSessionId && messages.length === 1 && !showLoader) {
        console.log("🔄 Restoring session on reload:", currentSessionId);

        if (
          currentSessionId.startsWith("guest-") ||
          currentSessionId.startsWith("local-")
        ) {
          return;
        }

        try {
          const { data, error } = await getChatMessages(currentSessionId);

          if (error || !data) {
            console.log("⚠️ Session not found, clearing");
            setCurrentSessionId(null);
            return;
          }

          if (data.length > 0) {
            const formattedMessages = data.map((msg) => ({
              text: msg.message_text,
              sender: msg.sender,
              timestamp: new Date(msg.created_at),
            }));

            console.log("✅ Session restored with", data.length, "messages");
            setMessages(formattedMessages);
          }
        } catch (error) {
          console.error("💥 Error restoring session:", error);
          setCurrentSessionId(null);
        }
      }
    };

    restoreSession();
  }, [currentSessionId, showLoader]);

  // Speech Recognition Functions
  const startListening = () => {
    if (recognitionRef.current && speechSupported) {
      setQuery("");
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
      console.log("🚀 handleSend triggered with query:", query);

      if (isListening) {
        stopListening();
      }

      const currentQuery = query;
      setQuery("");

      const userMessage = { text: currentQuery, sender: "user" };
      setMessages((prev) => [...prev, userMessage]);

      // ✅ Show typing indicator
      setIsTyping(true);

      let sessionId = currentSessionId;
      let isGuestUser = false;

      if (!sessionId) {
        console.log("🆕 Creating new session on first message...");

        try {
          const userWithRole = await getCurrentUserWithRole();

          if (userWithRole && userWithRole.id) {
            console.log("✅ Authenticated user detected:", userWithRole.email);

            try {
              const { data: sessionData, error } = await createChatSession(
                userWithRole.email,
                userWithRole.role,
                `Chat ${new Date().toLocaleTimeString()}`,
                userWithRole.id
              );

              if (sessionData && !error) {
                sessionId = sessionData.id;
                setCurrentSessionId(sessionId);

                const newChat = {
                  id: sessionData.id,
                  title: sessionData.title,
                  timestamp: "Now",
                  rawDate: new Date(sessionData.created_at),
                };
                setChatHistory((prev) => [newChat, ...prev]);
                console.log("✅ Authenticated session created:", sessionId);
              } else {
                throw new Error("Failed to create authenticated session");
              }
            } catch (error) {
              console.error("❌ Error creating authenticated session:", error);
              sessionId = `guest-${Date.now()}`;
              setCurrentSessionId(sessionId);
              isGuestUser = true;
              console.log("⚠️ Falling back to guest mode");
            }
          } else {
            sessionId = `guest-${Date.now()}`;
            setCurrentSessionId(sessionId);
            isGuestUser = true;
            console.log("🎭 Guest session created (no auth)");
          }
        } catch (error) {
          console.error("❌ Auth check error:", error);
          sessionId = `guest-${Date.now()}`;
          setCurrentSessionId(sessionId);
          isGuestUser = true;
          console.log("🎭 Guest session created (auth error)");
        }
      } else {
        isGuestUser =
          sessionId.startsWith("guest-") || sessionId.startsWith("local-");
        console.log(
          `📝 Using existing session: ${sessionId} (Guest: ${isGuestUser})`
        );
      }

      try {
        console.log("🔍 DEBUG - Session & Role Status:");
        console.log("   - sessionId:", sessionId);
        console.log("   - isGuestUser:", isGuestUser);
        console.log("   - userRole:", userRole);

        if (
          !isGuestUser &&
          !sessionId.startsWith("guest-") &&
          !sessionId.startsWith("local-")
        ) {
          console.log("💾 Saving user message to session:", sessionId);
          try {
            const { error } = await saveChatMessage(
              sessionId,
              currentQuery,
              "user"
            );
            if (error) {
              console.error("❌ Error saving user message:", error);
            } else {
              console.log("✅ User message saved to database");
            }
          } catch (error) {
            console.error("💥 Error saving message:", error);
          }
        }

        const actualUserRole = localStorage.getItem("userRole") || "guest";
        const actualIsGuest = actualUserRole === "guest";

        console.log("📤 Using role from localStorage:", actualUserRole);

        const requestData = {
          query: currentQuery,
          user_role: actualUserRole,
          user_data: userData,
          session_id: sessionId,
          is_guest: actualIsGuest,
        };

        console.log("📤 Sending request to backend:", requestData);

        const response = await fetch("http://localhost:5000/api/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestData),
        });

        console.log("📥 Response status:", response.status);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("✅ Backend response received");

        if (data.response) {
          const botMessage = {
            text: data.response,
            sender: "bot",
            access_restricted: data.access_restricted,
          };

          // ✅ Hide typing indicator before showing message
          setIsTyping(false);
          setMessages((prev) => [...prev, botMessage]);
          console.log("💬 Bot message added to chat");

          if (
            !isGuestUser &&
            !sessionId.startsWith("guest-") &&
            !sessionId.startsWith("local-")
          ) {
            console.log("💾 Saving bot message to session:", sessionId);
            try {
              const { error } = await saveChatMessage(
                sessionId,
                data.response,
                "bot"
              );
              if (error) {
                console.error("❌ Error saving bot message:", error);
              } else {
                console.log("✅ Bot message saved to database");
              }
            } catch (error) {
              console.error("💥 Error saving bot message:", error);
            }
          }

          if (
            data.suggested_title &&
            !isGuestUser &&
            !sessionId.startsWith("guest-") &&
            !sessionId.startsWith("local-")
          ) {
            console.log("🔄 Updating session title to:", data.suggested_title);
            try {
              const { error } = await updateChatSessionTitle(
                sessionId,
                data.suggested_title
              );
              if (!error) {
                setChatHistory((prev) =>
                  prev.map((chat) =>
                    chat.id === sessionId
                      ? { ...chat, title: data.suggested_title }
                      : chat
                  )
                );
                console.log("✅ Session title updated");
              }
            } catch (error) {
              console.error("❌ Error updating title:", error);
            }
          }
        }
      } catch (error) {
        console.error("💥 Fetch error:", error);
        setIsTyping(false); // ✅ Hide typing on error
        const errorMessage = {
          text: `Sorry, there was an error: ${error.message}. ${
            isGuestUser
              ? "Guest mode is active - your chat won't be saved."
              : ""
          }`,
          sender: "bot",
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    }
  };

  const isGenericTitle = (title) => {
    if (!title) return true;
    const genericTitles = [
      "chat",
      "new chat",
      "conversation",
      "discussion",
      "query",
    ];
    return genericTitles.includes(title.toLowerCase());
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSend();
    }
  };

  const handleLogout = async () => {
    console.log("🚪 LOGOUT INITIATED");
    localStorage.removeItem("currentSessionId");
    localStorage.clear();
    sessionStorage.clear();

    console.log("✅ Storage cleared:", {
      localStorage: localStorage.length,
      sessionStorage: sessionStorage.length,
    });

    sessionStorage.setItem("logoutInProgress", "true");

    try {
      await logoutUser();
      console.log("✅ Supabase logout complete");
    } catch (error) {
      console.error("⚠️ Supabase logout error (continuing anyway):", error);
    }

    sessionStorage.removeItem("logoutInProgress");
    window.location.href = "/login";
  };

  const handleNewChat = async () => {
    console.log("🆕 handleNewChat called - Starting new chat");
    localStorage.removeItem("currentSessionId");
    
    if (isListening) {
      stopListening();
    }

    try {
      const user = await getCurrentUser();
      console.log("👤 Current user:", user);

      if (user) {
        const title = `Chat ${new Date().toLocaleTimeString()}`;
        console.log("📝 Creating session for role:", userRole);

        const { data, error } = await createChatSession(
          user.email,
          userRole,
          title,
          user.id
        );

        if (error) {
          console.error("❌ Error creating chat session:", error);
          throw error;
        }

        if (data) {
          console.log("✅ New chat session created:", data.id);
          setCurrentSessionId(data.id);

          const newChat = {
            id: data.id,
            title: data.title,
            timestamp: "Now",
            rawDate: new Date(data.created_at),
          };
          setChatHistory((prev) => [newChat, ...prev]);
          console.log("📚 Chat history updated");
        }
      } else {
        const guestSessionId = `guest-${Date.now()}`;
        console.log("🎭 Guest session created:", guestSessionId);
        setCurrentSessionId(guestSessionId);
      }

      setMessages([
        {
          text: "Hello! Welcome to Samriddhi ChatBot. Ask me anything.",
          sender: "bot",
        },
      ]);
      setSidebarOpen(false);
    } catch (error) {
      console.error("💥 Error creating new chat session:", error);
      const fallbackSessionId = `local-${Date.now()}`;
      console.log("🔄 Falling back to local session:", fallbackSessionId);
      setCurrentSessionId(fallbackSessionId);
      setMessages([
        {
          text: "Hello! Welcome to Samriddhi ChatBot. Ask me anything.",
          sender: "bot",
        },
      ]);
      setSidebarOpen(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError("");
    setIsChangingPassword(true);

    if (passwordForm.newPassword.length < 6) {
      setPasswordError("Password must be at least 6 characters");
      setIsChangingPassword(false);
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError("Passwords do not match");
      setIsChangingPassword(false);
      return;
    }

    if (passwordForm.currentPassword === passwordForm.newPassword) {
      setPasswordError("New password must be different from current password");
      setIsChangingPassword(false);
      return;
    }

    try {
      const { createClient } = await import("@supabase/supabase-js");
      const supabase = createClient(
        import.meta.env.VITE_SUPABASE_URL,
        import.meta.env.VITE_SUPABASE_ANON_KEY
      );

      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: userInfo.email,
        password: passwordForm.currentPassword,
      });

      if (signInError) {
        setPasswordError("Current password is incorrect");
        setIsChangingPassword(false);
        return;
      }

      const { error: updateError } = await supabase.auth.updateUser({
        password: passwordForm.newPassword,
      });

      if (updateError) throw updateError;

      localStorage.setItem(`password_changed_${userInfo.email}`, "true");

      try {
        const tableName =
          userRole === "student" ? "students_data" : "teachers_data";
        await fetch("http://localhost:5000/api/mark-password-changed", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: userInfo.email,
            table: tableName,
          }),
        });
        console.log("✅ Password change status updated in database");
      } catch (dbError) {
        console.warn(
          "⚠️ Failed to update database, but localStorage updated:",
          dbError
        );
      }

      setPasswordSuccess(true);
      setShowChangePasswordModal(false);

      setTimeout(() => {
        setShowChangePasswordModal(false);
        setPasswordSuccess(false);
        setPasswordForm({
          currentPassword: "",
          newPassword: "",
          confirmPassword: "",
        });
        setIsChangingPassword(false);
      }, 2000);
    } catch (error) {
      console.error("Password change error:", error);
      setPasswordError(error.message || "Failed to change password");
      setIsChangingPassword(false);
    }
  };

  const handleDeleteChat = async (sessionId, e) => {
    e.stopPropagation();

    try {
      const { error } = await deleteChatSession(sessionId);

      if (error) throw error;

      setChatHistory((prev) => prev.filter((chat) => chat.id !== sessionId));

      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([
          {
            text: "Hello! Welcome to Samriddhi ChatBot. Ask me anything.",
            sender: "bot",
          },
        ]);
      }
    } catch (error) {
      console.error("Error deleting chat session:", error);
    }
  };

  if (showLoader) {
    return <Loader />;
  }

  return (
    <div className={`app-container ${darkMode ? "dark" : "light"}`}>
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 5V19M5 12H19"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
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
            chatHistory.map((chat) => (
              <div
                key={chat.id}
                className={`chat-history-item ${
                  currentSessionId === chat.id ? "active" : ""
                }`}
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
          <div
            className="profile-trigger"
            onClick={() => setProfileOpen(!profileOpen)}
          >
            <div className="profile-avatar">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle
                  cx="12"
                  cy="7"
                  r="4"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <span>My Profile</span>
            <svg
              className={`chevron ${profileOpen ? "up" : "down"}`}
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M18 15L12 9L6 15"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          {profileOpen && (
            <div className="profile-dropdown">
              <div className="profile-info">
                <div className="username">{userInfo.name}</div>
                <div className="email">{userInfo.email}</div>
                <div className="user-role">Role: {userInfo.role}</div>
              </div>

              {userRole !== "guest" && (
                <button
                  className="change-password-btn"
                  onClick={() => {
                    setShowChangePasswordModal(true);
                    setProfileOpen(false);
                  }}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <rect
                      x="3"
                      y="11"
                      width="18"
                      height="11"
                      rx="2"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                    <path
                      d="M7 11V7C7 5.67392 7.52678 4.40215 8.46447 3.46447C9.40215 2.52678 10.6739 2 12 2C13.3261 2 14.5979 2.52678 15.5355 3.46447C16.4732 4.40215 17 5.67392 17 7V11"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                  </svg>
                  Change Password
                </button>
              )}

              <button className="logout-btn" onClick={handleLogout}>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <polyline
                    points="16,17 21,12 16,7"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <line
                    x1="21"
                    y1="12"
                    x2="9"
                    y2="12"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Logout
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="main-content">
        {/* Header */}
        <div className="header">
          <div className="header-left">
            <button
              className="sidebar-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <line
                  x1="3"
                  y1="6"
                  x2="21"
                  y2="6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <line
                  x1="3"
                  y1="12"
                  x2="21"
                  y2="12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <line
                  x1="3"
                  y1="18"
                  x2="21"
                  y2="18"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <h1>AskSamriddhi</h1>
          </div>

          <div className="header-right">
            <div className="role-indicator"></div>
            <button
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
              title={`Switch to ${darkMode ? "light" : "dark"} mode`}
            >
              {darkMode ? (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="5"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="12"
                    y1="1"
                    x2="12"
                    y2="3"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="12"
                    y1="21"
                    x2="12"
                    y2="23"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="4.22"
                    y1="4.22"
                    x2="5.64"
                    y2="5.64"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="18.36"
                    y1="18.36"
                    x2="19.78"
                    y2="19.78"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="1"
                    y1="12"
                    x2="3"
                    y2="12"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="21"
                    y1="12"
                    x2="23"
                    y2="12"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="4.22"
                    y1="19.78"
                    x2="5.64"
                    y2="18.36"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <line
                    x1="18.36"
                    y1="5.64"
                    x2="19.78"
                    y2="4.22"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                </svg>
              ) : (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
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
                  <div className="access-warning">Access Restricted</div>
                )}
                {msg.sender === "bot" ? (
                  <FormattedMessage text={msg.text} />
                ) : (
                  msg.text
                )}
              </div>
            ))}
            
            {/* ✅ Typing Indicator */}
            {isTyping && (
              <div className="message bot typing-indicator">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            
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
              placeholder={
                isListening
                  ? "Listening..."
                  : "Type your question or click the mic to speak..."
              }
              className={transcript ? "listening-input" : ""}
            />

            {/* Speech Recognition Button */}
            {speechSupported && (
              <button
                className={`mic-btn ${isListening ? "listening" : ""}`}
                onClick={isListening ? stopListening : startListening}
                title={isListening ? "Stop listening" : "Start voice input"}
              >
                {isListening ? (
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <rect
                      x="6"
                      y="4"
                      width="4"
                      height="16"
                      rx="2"
                      fill="currentColor"
                    />
                    <rect
                      x="14"
                      y="4"
                      width="4"
                      height="16"
                      rx="2"
                      fill="currentColor"
                    />
                  </svg>
                ) : (
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M12 2C13.1046 2 14 2.89543 14 4V12C14 13.1046 13.1046 14 12 14C10.8954 14 10 13.1046 10 12V4C10 2.89543 10.8954 2 12 2Z"
                      fill="currentColor"
                    />
                    <path
                      d="M19 10V12C19 16.4183 15.4183 20 11 20H13C17.4183 20 21 16.4183 21 12V10H19Z"
                      fill="currentColor"
                    />
                    <path
                      d="M5 10V12C5 16.4183 8.58172 20 13 20H11C6.58172 20 3 16.4183 3 12V10H5Z"
                      fill="currentColor"
                    />
                    <rect
                      x="11"
                      y="20"
                      width="2"
                      height="4"
                      fill="currentColor"
                    />
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

      {/* Password Change Modal */}
      {showChangePasswordModal && (
        <div
          className="modal-overlay"
          onClick={() =>
            !isChangingPassword && setShowChangePasswordModal(false)
          }
        >
          <div className="password-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Change Password</h3>
              <button
                className="close-modal"
                onClick={() =>
                  !isChangingPassword && setShowChangePasswordModal(false)
                }
                disabled={isChangingPassword}
              >
                ×
              </button>
            </div>

            {passwordSuccess ? (
              <div className="success-message">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="#10b981"
                    strokeWidth="2"
                  />
                  <path
                    d="M8 12L11 15L16 9"
                    stroke="#10b981"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p>Password changed successfully!</p>
              </div>
            ) : (
              <form onSubmit={handlePasswordChange}>
                <div className="form-group">
                  <label>Current Password</label>
                  <input
                    type="password"
                    value={passwordForm.currentPassword}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        currentPassword: e.target.value,
                      })
                    }
                    disabled={isChangingPassword}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>New Password</label>
                  <input
                    type="password"
                    value={passwordForm.newPassword}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        newPassword: e.target.value,
                      })
                    }
                    placeholder="At least 6 characters"
                    disabled={isChangingPassword}
                    required
                  />
                  {passwordForm.newPassword && (
                    <div className="password-strength">
                      Strength:{" "}
                      {passwordForm.newPassword.length < 6
                        ? "❌ Too short"
                        : passwordForm.newPassword.length < 8
                        ? "⚠️ Weak"
                        : "✅ Good"}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label>Confirm New Password</label>
                  <input
                    type="password"
                    value={passwordForm.confirmPassword}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        confirmPassword: e.target.value,
                      })
                    }
                    disabled={isChangingPassword}
                    required
                  />
                </div>

                {passwordError && (
                  <div className="error-message">❌ {passwordError}</div>
                )}

                <button
                  type="submit"
                  className="submit-btn"
                  disabled={isChangingPassword}
                >
                  {isChangingPassword
                    ? "Changing Password..."
                    : "Change Password"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatBot;