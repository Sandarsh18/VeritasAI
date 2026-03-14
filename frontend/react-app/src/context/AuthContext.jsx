import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getMe, login as loginApi, logout as logoutApi, register as registerApi, updateProfile as updateProfileApi } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('veritasai_token'));
  const [isLoading, setIsLoading] = useState(true);

  const clearAuth = () => {
    localStorage.removeItem('veritasai_token');
    setToken(null);
    setUser(null);
  };

  const login = async (username_or_email, password, remember_me = false) => {
    const data = await loginApi({ username_or_email, password, remember_me });
    localStorage.setItem('veritasai_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const register = async (formData) => {
    return registerApi(formData);
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch {
      // noop
    }
    clearAuth();
  };

  const updateProfile = async (data) => {
    const updated = await updateProfileApi(data);
    setUser((prev) => ({ ...prev, ...updated }));
    return updated;
  };

  useEffect(() => {
    const validate = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await getMe();
        setUser(me);
      } catch {
        clearAuth();
      } finally {
        setIsLoading(false);
      }
    };
    validate();
  }, [token]);

  const value = useMemo(() => ({
    user,
    token,
    login,
    register,
    logout,
    updateProfile,
    isAuthenticated: !!user,
    isLoading,
  }), [user, token, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
