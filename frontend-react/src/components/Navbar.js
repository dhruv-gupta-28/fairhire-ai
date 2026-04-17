import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  BarChart3,
  FileText,
  Briefcase,
  History,
  LogOut,
  User,
} from "lucide-react";

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { path: "/dashboard", label: "Dashboard", icon: BarChart3 },
    { path: "/analysis", label: "Bias Analysis", icon: BarChart3 },
    { path: "/resume-analysis", label: "Resume", icon: FileText },
    { path: "/job-matching", label: "Jobs", icon: Briefcase },
    { path: "/history", label: "History", icon: History },
  ];

  return (
    <nav
      className="fixed top-0 left-0 w-full z-[1000]"
      style={{
        background: "#0a0a0a",
        borderBottom: "1px solid #1e1e1e",
      }}
    >
      <div className="max-w-[960px] mx-auto px-5">
        <div className="flex justify-between h-14 items-center">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-white">FairHire AI</span>
          </Link>

          {/* Navigation */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs transition-all duration-200 ${
                    isActive
                      ? "bg-blue-600/15 text-blue-400 font-semibold"
                      : "text-gray-400 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}

            {/* User & Logout */}
            <div className="flex items-center gap-2 ml-3 pl-3 border-l border-gray-800">
              <Link
                to="/profile"
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs transition-all ${
                  location.pathname === "/profile"
                    ? "bg-blue-600/15 text-blue-400 font-semibold"
                    : "text-gray-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <User className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Profile</span>
              </Link>

              <button
                onClick={handleLogout}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                aria-label="Logout"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
