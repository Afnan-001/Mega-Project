import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  authApi, 
  healthApi, 
  getStoredToken, 
  setStoredToken, 
  getStoredUser, 
  setStoredUser 
} from '../services/api';

const AuthContext = createContext(null);

export const demoAccounts = {
  teacher: {
    id: 'prof-mercer-01',
    name: 'Prof. Alex Mercer',
    email: 'teacher@university.edu',
    password: 'StrongPassword123!',
    role: 'teacher',
    department: 'Computer Science & AI',
    title: 'Senior Faculty / Professor',
    avatar: 'AM',
  },
  student: {
    id: 'stud-sarah-01',
    name: 'Sarah Chen',
    email: 'student@university.edu',
    password: 'StrongPassword123!',
    role: 'student',
    department: 'Computer Science Undergrad',
    title: '3rd Year Undergraduate',
    avatar: 'SC',
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());
  const [authError, setAuthError] = useState(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [isCheckingServer, setIsCheckingServer] = useState(true);

  // Check backend server health on mount
  useEffect(() => {
    async function checkServer() {
      try {
        await healthApi.checkHealth();
        setServerOnline(true);
      } catch (err) {
        // Backend not currently reachable
        setServerOnline(false);
      } finally {
        setIsCheckingServer(false);
      }
    }
    checkServer();
  }, []);

  // Validate active JWT session on startup
  useEffect(() => {
    async function validateSession() {
      const token = getStoredToken();
      if (!token) return;
      try {
        const me = await authApi.getMe();
        if (me && me.email) {
          const updatedUser = {
            id: me.id,
            name: me.full_name,
            email: me.email,
            role: me.role,
            department: me.role === 'teacher' ? 'Computer Science & AI' : 'Computer Science Undergrad',
            title: me.role === 'teacher' ? 'Faculty Professor' : 'Undergraduate Student',
            avatar: (me.full_name || 'User').split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase(),
            token,
          };
          setUser(updatedUser);
          setStoredUser(updatedUser);
        }
      } catch (err) {
        console.warn('Session token validation failed or expired:', err.message);
      }
    }

    if (serverOnline) {
      validateSession();
    }
  }, [serverOnline]);

  /**
   * Real API Login with automatic fallback to demo profile if offline
   */
  const login = async (role, credentials = {}) => {
    setAuthError(null);
    const demo = demoAccounts[role];
    const emailToUse = credentials.email || demo.email;
    const passwordToUse = credentials.password || demo.password || 'StrongPassword123!';

    try {
      // 1. Attempt real API login
      const res = await authApi.login({
        email: emailToUse,
        password: passwordToUse,
      });

      const loggedInUser = {
        id: res.user_id || res.id || 'usr_' + Date.now(),
        name: res.full_name || credentials.name || demo.name,
        email: res.email || emailToUse,
        role: res.role || role,
        department: (res.role || role) === 'teacher' ? 'Computer Science & AI' : 'Computer Science Undergrad',
        title: (res.role || role) === 'teacher' ? 'Senior Faculty / Professor' : '3rd Year Undergraduate',
        avatar: (res.full_name || demo.name).split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase(),
        token: res.access_token,
      };

      setStoredToken(res.access_token);
      setStoredUser(loggedInUser);
      setUser(loggedInUser);
      setServerOnline(true);
      return loggedInUser;
    } catch (apiError) {
      console.warn('Backend login attempt returned error/offline:', apiError.message);

      // If backend explicitly rejected invalid credentials (400 / 401), pass error back
      if (apiError.status === 400 || apiError.status === 401) {
        setAuthError(apiError.message || 'Invalid email or password.');
        throw apiError;
      }

      // If backend is unreachable or in development/offline mode, permit demo fallback
      const fallbackUser = {
        ...demo,
        email: emailToUse,
        name: credentials.name || demo.name,
        role: role,
        token: 'demo-token-' + Date.now(),
        isDemoSession: true,
      };

      setStoredToken(fallbackUser.token);
      setStoredUser(fallbackUser);
      setUser(fallbackUser);
      return fallbackUser;
    }
  };

  /**
   * Register a new user via FastAPI
   */
  const register = async ({ email, password, full_name, role }) => {
    setAuthError(null);
    try {
      const res = await authApi.register({ email, password, full_name, role });
      const newUser = {
        id: res.user_id || 'usr_' + Date.now(),
        name: res.full_name || full_name,
        email: email,
        role: res.role || role,
        department: role === 'teacher' ? 'Computer Science & AI' : 'Computer Science Undergrad',
        title: role === 'teacher' ? 'Faculty Professor' : 'Undergraduate Student',
        avatar: (full_name || 'User').split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase(),
        token: res.access_token,
      };

      setStoredToken(res.access_token);
      setStoredUser(newUser);
      setUser(newUser);
      return newUser;
    } catch (err) {
      setAuthError(err.message || 'Registration failed');
      throw err;
    }
  };

  const logout = () => {
    setUser(null);
    setStoredToken(null);
    setStoredUser(null);
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      isAuthenticated: !!user, 
      role: user?.role, 
      login, 
      register, 
      logout, 
      authError, 
      setAuthError,
      serverOnline,
      isCheckingServer 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
