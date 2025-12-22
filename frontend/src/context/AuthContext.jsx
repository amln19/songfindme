import { createContext, useContext, useState, useEffect, useMemo } from "react";
import toast from "react-hot-toast";
import { apiEndpoints } from "../api";

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const parseJwt = (token) => {
    try {
      return JSON.parse(atob(token.split(".")[1]));
    } catch (e) {
      return null;
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      const decoded = parseJwt(token);
      if (decoded) {
        setUser({ username: decoded.sub, role: decoded.role, token });
      } else {
        localStorage.removeItem("access_token");
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    try {
      const res = await fetch(apiEndpoints.login, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Invalid credentials");

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);

      const decoded = parseJwt(data.access_token);
      setUser({
        username: decoded.sub,
        role: decoded.role,
        token: data.access_token,
      });

      toast.success(`Welcome back, ${decoded.sub}!`);
      return true;
    } catch (error) {
      toast.error(error.message);
      return false;
    }
  };

  const signup = async (username, password) => {
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    try {
      const res = await fetch(apiEndpoints.register, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Registration failed");
      }

      toast.success("Account created! Please login.");
      return true;
    } catch (error) {
      toast.error(error.message);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
    toast.success("Logged out successfully");
  };

  // Memoize context value to prevent unnecessary re-renders
  const value = useMemo(
    () => ({ user, login, signup, logout, loading }),
    [user, loading]
  );

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};