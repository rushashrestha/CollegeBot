// src/services/authService.js
import { 
  signInWithEmailAndPassword, 
  signOut, 
  updatePassword,
  onAuthStateChanged,
  sendPasswordResetEmail
} from 'firebase/auth';
import { 
  doc, 
  getDoc, 
  updateDoc, 
  collection, 
  query, 
  where, 
  getDocs,
  orderBy,
  limit
} from 'firebase/firestore';
import { auth, db } from '../firebase/firebase';

class AuthService {
  constructor() {
    this.currentUser = null;
    this.userRole = null;
    this.userDetails = null;
    this.isLoading = true;
    this.authStateListeners = [];
    
    // Set up auth state listener
    this.setupAuthStateListener();
  }
  
  setupAuthStateListener() {
    onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          await this.loadUserData(user);
        } catch (error) {
          console.error('Error loading user data:', error);
          this.currentUser = null;
          this.userRole = null;
          this.userDetails = null;
        }
      } else {
        this.currentUser = null;
        this.userRole = null;
        this.userDetails = null;
      }
      this.isLoading = false;
      
      // Notify all listeners
      this.authStateListeners.forEach(callback => callback({
        user: this.currentUser,
        userRole: this.userRole,
        userDetails: this.userDetails,
        isLoading: this.isLoading
      }));
    });
  }
  
  // Subscribe to auth state changes
  onAuthStateChanged(callback) {
    this.authStateListeners.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.authStateListeners.indexOf(callback);
      if (index > -1) {
        this.authStateListeners.splice(index, 1);
      }
    };
  }
  
  async loadUserData(user) {
    this.currentUser = user;
    
    // Get basic user info
    const userDoc = await getDoc(doc(db, 'users', user.uid));
    if (userDoc.exists()) {
      const userData = userDoc.data();
      this.userRole = userData.role;
      
      // Get detailed user data from appropriate collection
      if (userData.role === 'student') {
        const studentDoc = await getDoc(doc(db, 'students', user.uid));
        this.userDetails = studentDoc.exists() ? studentDoc.data() : userData;
      } else if (userData.role === 'teacher') {
        const teacherDoc = await getDoc(doc(db, 'teachers', user.uid));
        this.userDetails = teacherDoc.exists() ? teacherDoc.data() : userData;
      }
      
      // Update last login
      await updateDoc(doc(db, 'users', user.uid), {
        lastLogin: new Date()
      });
    }
  }
  
  // Login function
  async login(email, password) {
    try {
      // Validate email format first
      if (!this.validateEmailFormat(email)) {
        throw new Error('Invalid email format. Use name.surname@samriddhi.edu.np for students or name.surname@samriddhi.com for staff');
      }
      
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;
      
      // Load user data
      await this.loadUserData(user);
      
      // Check if password change is required
      const requiresPasswordChange = this.userDetails?.mustChangePassword || false;
      
      return {
        success: true,
        user: this.currentUser,
        role: this.userRole,
        details: this.userDetails,
        requiresPasswordChange
      };
      
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: this.getErrorMessage(error)
      };
    }
  }
  
  // Change password function
  async changePassword(newPassword, confirmPassword) {
    try {
      if (!this.currentUser) {
        throw new Error('No user logged in');
      }
      
      if (newPassword !== confirmPassword) {
        throw new Error('Passwords do not match');
      }
      
      if (newPassword.length < 8) {
        throw new Error('Password must be at least 8 characters long');
      }
      
      // Update password in Firebase Auth
      await updatePassword(this.currentUser, newPassword);
      
      // Update flags in Firestore
      await updateDoc(doc(db, 'users', this.currentUser.uid), {
        mustChangePassword: false,
        passwordChangedAt: new Date(),
        tempPassword: null // Remove temp password
      });
      
      // Update detailed collection too
      const collection_name = this.userRole === 'student' ? 'students' : 'teachers';
      await updateDoc(doc(db, collection_name, this.currentUser.uid), {
        mustChangePassword: false,
        passwordChangedAt: new Date(),
        tempPassword: null
      });
      
      // Reload user data
      await this.loadUserData(this.currentUser);
      
      return { success: true };
      
    } catch (error) {
      console.error('Password change error:', error);
      return {
        success: false,
        error: this.getErrorMessage(error)
      };
    }
  }
  
  // Logout function
  async logout() {
    try {
      await signOut(auth);
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return {
        success: false,
        error: this.getErrorMessage(error)
      };
    }
  }
  
  // Reset password
  async resetPassword(email) {
    try {
      await sendPasswordResetEmail(auth, email);
      return { success: true };
    } catch (error) {
      console.error('Password reset error:', error);
      return {
        success: false,
        error: this.getErrorMessage(error)
      };
    }
  }
  
  // Validate email format
  validateEmailFormat(email) {
    const studentPattern = /^[a-zA-Z]+(\.[a-zA-Z]+)*@samriddhi\.edu\.np$/;
    const teacherPattern = /^[a-zA-Z]+(\.[a-zA-Z]+)*@samriddhi\.com$/;
    
    return studentPattern.test(email) || teacherPattern.test(email);
  }
  
  // Get user role
  getUserRole() {
    return this.userRole;
  }
  
  // Check if user is teacher
  isTeacher() {
    return this.userRole === 'teacher';
  }
  
  // Check if user is student
  isStudent() {
    return this.userRole === 'student';
  }
  
  // Get current user details
  getCurrentUser() {
    return this.currentUser;
  }
  
  // Get detailed user info
  getUserDetails() {
    return this.userDetails;
  }
  
  // Get current auth state
  getAuthState() {
    return {
      user: this.currentUser,
      userRole: this.userRole,
      userDetails: this.userDetails,
      isLoading: this.isLoading,
      isAuthenticated: !!this.currentUser,
      isTeacher: this.userRole === 'teacher',
      isStudent: this.userRole === 'student',
      requiresPasswordChange: this.userDetails?.mustChangePassword || false
    };
  }
  
  // Query student data (for chatbot)
  async queryStudentData(searchTerm = '', filters = {}) {
    try {
      if (!this.isTeacher()) {
        throw new Error('Access denied. Only teachers can query student data.');
      }
      
      let q = collection(db, 'students');
      const conditions = [];
      
      // Add filters
      if (filters.program) {
        conditions.push(where('program', '>=', filters.program));
        conditions.push(where('program', '<=', filters.program + '\uf8ff'));
      }
      if (filters.batch) {
        conditions.push(where('batch', '==', filters.batch));
      }
      if (filters.section) {
        conditions.push(where('section', '==', filters.section));
      }
      
      // Build query
      if (conditions.length > 0) {
        q = query(q, ...conditions, limit(50));
      } else {
        q = query(q, limit(50));
      }
      
      const querySnapshot = await getDocs(q);
      const results = [];
      
      querySnapshot.forEach((doc) => {
        const data = doc.data();
        // Apply text search if provided
        if (!searchTerm || 
            data.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            data.program?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            data.rollNo?.toString().includes(searchTerm)) {
          results.push({
            id: doc.id,
            ...data
          });
        }
      });
      
      return { success: true, data: results };
      
    } catch (error) {
      console.error('Query error:', error);
      return {
        success: false,
        error: this.getErrorMessage(error)
      };
    }
  }
  
  // Get my own data (for students)
  async getMyData() {
    try {
      if (!this.currentUser) {
        throw new Error('Not authenticated');
      }
      
      return {
        success: true,
        data: this.userDetails
      };
      
    } catch (error) {
      console.error('Error fetching user data:', error);
      return {
        success: false,
        error: this.getErrorMessage(error)
      };
    }
  }
  
  // Error message handler
  getErrorMessage(error) {
    switch (error.code) {
      case 'auth/user-not-found':
        return 'No account found with this email address.';
      case 'auth/wrong-password':
        return 'Incorrect password.';
      case 'auth/invalid-email':
        return 'Invalid email address format.';
      case 'auth/too-many-requests':
        return 'Too many failed attempts. Please try again later.';
      case 'auth/weak-password':
        return 'Password is too weak. Use at least 8 characters.';
      case 'auth/requires-recent-login':
        return 'Please log out and log back in to change your password.';
      default:
        return error.message || 'An unexpected error occurred.';
    }
  }
}

// Create and export a single instance
const authService = new AuthService();
export default authService;