import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // 🔥 SET BASE URL (AUTO PROXY OR ENV)
  axios.defaults.baseURL = process.env.REACT_APP_API_URL || "";
  axios.defaults.withCredentials = true;

  useEffect(() => {
    const storedUser = localStorage.getItem("user");

    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        setUser({});
      }
    }

    setLoading(false);
  }, []);

  // 🔥 LOGIN
  const login = async (email, password) => {
    try {
      const response = await axios.post("/auth/login", { email, password });

      const { user: userData } = response.data;

      const userObj = {
        email: userData.email,
        role: userData.role,
      };

      // ✅ FIX: just cache user details (token handled via HttpOnly cookie)
      localStorage.setItem("user", JSON.stringify(userObj));

      setUser(userObj);

      return { success: true };

    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || "Login failed",
      };
    }
  };

  // 🔥 REGISTER
  const register = async (email, password, role = "user") => {
    try {
      const response = await axios.post("/auth/register", {
        email,
        password,
        role,
      });

      const { user: userData } = response.data;

      const userObj = {
        email: userData.email,
        role: userData.role,
      };

      localStorage.setItem("user", JSON.stringify(userObj));

      setUser(userObj);

      return { success: true };

    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || "Registration failed",
      };
    }
  };

  // 🔥 LOGOUT
  const logout = async () => {
    try {
      await axios.post("/auth/logout");
    } catch (err) {
      console.warn("Logout request failed cleanly");
    } finally {
      localStorage.removeItem("user");
      setUser(null);
    }
  };

  const value = {
    user,
    login,
    register,
    logout,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};