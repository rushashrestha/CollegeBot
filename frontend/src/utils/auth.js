// auth.js
import { supabase } from "./supabase";

// Login user
export const loginUser = async (email, password) => {
  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    return { data, error: null };
  } catch (error) {
    // Supabase errors are often wrapped, this attempts to return the message.
    return { data: null, error: error.message || "Invalid credentials" };
  }
};

// Get current session
export const getCurrentSession = async () => {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();
  if (error) throw error;
  return session;
};

// Get current user
export const getCurrentUser = async () => {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error) throw error;
  return user;
};

// Logout user
export const logoutUser = async () => {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
};

// Listen to auth state changes
export const onAuthStateChange = (callback) => {
  return supabase.auth.onAuthStateChange(callback);
};

// ============ ROLE-BASED FUNCTIONS ============

// Get user role from database
export const getUserRole = async (email) => {
  try {
    // Check in teachers table
    const { data: teacherData, error: teacherError } = await supabase
      .from('teachers_data')
      .select('email')
      .eq('email', email)
      .single();

    if (teacherData && !teacherError) {
      return 'teacher';
    }

    // Check in students table
    const { data: studentData, error: studentError } = await supabase
      .from('students_data')
      .select('email')
      .eq('email', email)
      .single();

    if (studentData && !studentError) {
      return 'student';
    }

    // Check in admin table (you might need to create this)
    const { data: adminData, error: adminError } = await supabase
      .from('admin_users')
      .select('email')
      .eq('email', email)
      .single();

    if (adminData && !adminError) {
      return 'admin';
    }

    return 'guest';
  } catch (error) {
    console.error('Error fetching user role:', error);
    return 'guest';
  }
};

// Enhanced login function with role detection
export const loginUserWithRole = async (email, password) => {
  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (data.user) {
      const userRole = await getUserRole(email);
      return { data: { ...data, userRole }, error: null };
    }

    return { data, error };
  } catch (error) {
    return { data: null, error: error.message || "Invalid credentials" };
  }
};

// Get current user with role
export const getCurrentUserWithRole = async () => {
  try {
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser();
    
    if (error) throw error;
    
    if (user) {
      const userRole = await getUserRole(user.email);
      return { ...user, role: userRole };
    }
    
    return null;
  } catch (error) {
    console.error('Error getting user with role:', error);
    return null;
  }
};

// ============ CHAT HISTORY FUNCTIONS ============

// Chat History Functions
export const createChatSession = async (userEmail, userRole, title, userId = null) => {
  try {
    const { data, error } = await supabase
      .from('chat_sessions')
      .insert([
        {
          user_id: userId,
          user_email: userEmail,
          user_role: userRole,
          title: title
        }
      ])
      .select()
      .single();

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    console.error('Error creating chat session:', error);
    return { data: null, error: error.message };
  }
};

export const saveChatMessage = async (sessionId, messageText, sender) => {
  try {
    const { data, error } = await supabase
      .from('chat_messages')
      .insert([
        {
          session_id: sessionId,
          message_text: messageText,
          sender: sender
        }
      ])
      .select()
      .single();

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    console.error('Error saving chat message:', error);
    return { data: null, error: error.message };
  }
};

export const getUserChatSessions = async (userId) => {
  try {
    const { data, error } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    console.error('Error fetching chat sessions:', error);
    return { data: null, error: error.message };
  }
};

export const getChatMessages = async (sessionId) => {
  try {
    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true });

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    console.error('Error fetching chat messages:', error);
    return { data: null, error: error.message };
  }
};

export const updateChatSessionTitle = async (sessionId, title) => {
  try {
    const { data, error } = await supabase
      .from('chat_sessions')
      .update({ title: title, updated_at: new Date().toISOString() })
      .eq('id', sessionId)
      .select()
      .single();

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    console.error('Error updating chat session:', error);
    return { data: null, error: error.message };
  }
};

export const deleteChatSession = async (sessionId) => {
  try {
    const { error } = await supabase
      .from('chat_sessions')
      .delete()
      .eq('id', sessionId);

    if (error) throw error;
    return { error: null };
  } catch (error) {
    console.error('Error deleting chat session:', error);
    return { error: error.message };
  }
};

// ============ AUTO TITLE GENERATION FUNCTIONS ============

// Function to auto-generate chat title from the first user message
export const generateChatTitle = (message) => {
  if (!message || message.trim().length === 0) {
    return "New Chat";
  }

  const messageLower = message.toLowerCase().trim();
  
  // Extract key entities for title
  if (messageLower.includes('course') || messageLower.includes('subject') || 
      messageLower.includes('syllabus') || messageLower.includes('curriculum')) {
    if (messageLower.includes('csit')) {
      return "CSIT Course Information";
    } else if (messageLower.includes('bca')) {
      return "BCA Course Information";
    } else if (messageLower.includes('bsw')) {
      return "BSW Course Information";
    } else if (messageLower.includes('bbs')) {
      return "BBS Course Information";
    } else {
      return "Course Information";
    }
  }
  
  else if (messageLower.includes('who is') || messageLower.includes('information about') || 
           messageLower.includes('tell me about')) {
    // Extract name from query
    const nameMatch = messageLower.match(/(?:who is|information about|tell me about)\s+([^?\.]*)/);
    if (nameMatch && nameMatch[1]) {
      const name = nameMatch[1].trim();
      if (name.length > 0) {
        return `About ${name.charAt(0).toUpperCase() + name.slice(1)}`;
      }
    }
    return "{name} Information";
  }
  
  else if (messageLower.includes('email') || messageLower.includes('phone') || 
           messageLower.includes('contact')) {
    return "Contact Information";
  }
  
  else if (messageLower.includes('admission') || messageLower.includes('eligibility') || 
           messageLower.includes('fee')) {
    return "Admission Information";
  }
  
  else if (messageLower.includes('facility') || messageLower.includes('library') || 
           messageLower.includes('lab')) {
    return "College Facilities";
  }
  
  else if (messageLower.includes('program') || messageLower.includes('degree')) {
    return "Academic Programs";
  }
  
  else if (messageLower.includes('teacher') || messageLower.includes('faculty')) {
    return "Faculty Information";
  }
  
  else if (messageLower.includes('student')) {
    return "Student Information";
  }
  
  else if (messageLower.includes('semester') || messageLower.includes('credit')) {
    return "Academic Information";
  }
  
  else {
    // Use first few meaningful words of the question
    const words = message.split(/\s+/).filter(word => 
      word.length > 2 && 
      !['what', 'how', 'when', 'where', 'why', 'who', 'which', 'tell', 'me', 'about', 'information'].includes(word.toLowerCase())
    );
    
    if (words.length > 0) {
      const meaningfulWords = words.slice(0, 4);
      let title = meaningfulWords.join(' ');
      
      // Capitalize first letter of each word for title case
      title = title.split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
      
      return title.length > 30 ? title.substring(0, 30) + '...' : title;
    }
    
    // Fallback: use first 4 words of the message
    const firstWords = message.split(/\s+/).slice(0, 4).join(' ');
    return firstWords.length > 30 ? firstWords.substring(0, 30) + '...' : firstWords;
  }
};

// Enhanced create chat session with auto-title generation
export const createChatSessionWithAutoTitle = async (userEmail, userRole, firstMessage, userId = null) => {
  try {
    const title = generateChatTitle(firstMessage);
    
    const { data, error } = await supabase
      .from('chat_sessions')
      .insert([
        {
          user_id: userId,
          user_email: userEmail,
          user_role: userRole,
          title: title
        }
      ])
      .select()
      .single();

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    console.error('Error creating chat session:', error);
    return { data: null, error: error.message };
  }
};

// Function to update chat title based on conversation content
export const updateChatTitleFromMessages = async (sessionId) => {
  try {
    // Get all messages for this session
    const { data: messages, error } = await supabase
      .from('chat_messages')
      .select('message_text, sender')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true });

    if (error) throw error;

    if (messages && messages.length > 0) {
      // Find the first user message to generate title from
      const firstUserMessage = messages.find(msg => msg.sender === 'user');
      if (firstUserMessage) {
        const newTitle = generateChatTitle(firstUserMessage.message_text);
        
        // Update the session title
        const { data, error: updateError } = await supabase
          .from('chat_sessions')
          .update({ title: newTitle, updated_at: new Date().toISOString() })
          .eq('id', sessionId)
          .select()
          .single();

        if (updateError) throw updateError;
        return { data, error: null };
      }
    }
    
    return { data: null, error: 'No user messages found' };
  } catch (error) {
    console.error('Error updating chat title from messages:', error);
    return { data: null, error: error.message };
  }
};