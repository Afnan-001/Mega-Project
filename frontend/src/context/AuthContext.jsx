import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const demoAccounts = {
  teacher: {
    id: 'prof-mercer-01',
    name: 'Prof. Alex Mercer',
    email: 'alex.mercer@university.edu',
    role: 'teacher',
    department: 'Computer Science & AI',
    title: 'Senior Faculty / Professor',
    avatar: 'AM',
  },
  student: {
    id: 'stud-sarah-01',
    name: 'Sarah Chen',
    email: 'sarah.chen@student.edu',
    role: 'student',
    department: 'Computer Science Undergrad',
    title: '3rd Year Undergraduate',
    avatar: 'SC',
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('edugraph_auth_user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch (e) {
      console.error('Error reading auth from localStorage', e);
      return null;
    }
  });

  const [authError, setAuthError] = useState(null);

  const login = (role, credentials = {}) => {
    setAuthError(null);
    const demo = demoAccounts[role];
    
    // Support customized email/name if provided
    const loggedInUser = {
      ...demo,
      email: credentials.email || demo.email,
      name: credentials.name || demo.name,
      role: role,
      token: 'jwt-token-simulated-' + Date.now()
    };

    setUser(loggedInUser);
    localStorage.setItem('edugraph_auth_user', JSON.stringify(loggedInUser));
    return loggedInUser;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('edugraph_auth_user');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, role: user?.role, login, logout, authError, setAuthError }}>
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
