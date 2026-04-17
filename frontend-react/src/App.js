import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Login from "./components/Login";
import Register from "./components/Register";
import Landing from "./components/Landing";
import Dashboard from "./components/Dashboard";
import Analysis from "./components/Analysis";
import ResumeAnalysis from "./components/ResumeAnalysis";
import JobMatching from "./components/JobMatching";
import History from "./components/History";
import Profile from "./components/Profile";
import Navbar from "./components/Navbar";
import "./App.css";

// 🔒 Protected Route
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="flex items-center text-gray-300">
          <div className="loading mr-3 border-blue-500"></div>
          Loading...
        </div>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" />;
};

// 🔥 Layout Wrapper
const Layout = ({ children }) => {
  return (
    <div className="content">
      <Navbar />
      <div className="page-container">{children}</div>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen text-white">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/analysis"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Analysis />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/resume-analysis"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ResumeAnalysis />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/job-matching"
              element={
                <ProtectedRoute>
                  <Layout>
                    <JobMatching />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/history"
              element={
                <ProtectedRoute>
                  <Layout>
                    <History />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Profile />
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
