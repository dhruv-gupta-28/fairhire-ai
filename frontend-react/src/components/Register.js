import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Mail, Lock, Eye, EyeOff, User, CheckCircle } from "lucide-react";

const Register = () => {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    role: "user",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      setLoading(false);
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      setLoading(false);
      return;
    }

    const result = await register(
      formData.email,
      formData.password,
      formData.role,
    );

    if (result.success) {
      setSuccess(true);
      setTimeout(() => navigate("/dashboard"), 1000);
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="register min-h-screen flex items-center justify-center px-4 bg-[#0a0a0a]">
      <div className="glass p-6 w-full max-w-sm border border-white/5 shadow-xl rounded-xl space-y-4">
        <div className="text-center mb-4">
          <div className="mx-auto w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
            <User className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-1">Create Account</h2>
          <p className="text-gray-500 text-xs">Join FairHire AI</p>
        </div>

        {/* 🔥 ERROR / SUCCESS */}
        {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm">{error}</div>}
        {success && <div className="bg-green-500/10 border border-green-500/20 text-green-400 px-4 py-3 rounded-lg text-sm flex items-center"><CheckCircle className="w-4 h-4 mr-2" /> Registration successful! Redirecting...</div>}

        {/* 🔥 FORM */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="relative">
            <input
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="input-modern w-full !pl-10"
              placeholder="Email"
            />
            <Mail className="absolute left-3 top-2.5 text-gray-400" size={18} />
          </div>

          <select
            name="role"
            value={formData.role}
            onChange={handleChange}
            className="input-modern w-full"
          >
            <option value="user">Job Seeker</option>
            <option value="recruiter">Recruiter</option>
            <option value="admin">Admin</option>
          </select>

          <div className="relative">
            <input
              name="password"
              type={showPassword ? "text" : "password"}
              required
              value={formData.password}
              onChange={handleChange}
              className="input-modern w-full !pl-10 !pr-10"
              placeholder="Password"
            />
            <Lock className="absolute left-3 top-2.5 text-gray-400" size={18} />

            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-2.5 text-gray-400"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <div className="relative">
            <input
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              required
              value={formData.confirmPassword}
              onChange={handleChange}
              className="input-modern w-full !pl-10 !pr-10"
              placeholder="Confirm Password"
            />
            <Lock className="absolute left-3 top-2.5 text-gray-400" size={18} />

            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-2.5 text-gray-400"
            >
              {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button type="submit" disabled={loading || success} className="btn-primary w-full flex justify-center items-center">
            {loading ? (
              <>
                 <div className="loading mr-2 border-blue-200"></div>
                 Creating...
              </>
            ) : "Register"}
          </button>
        </form>

        {/* 🔥 FOOTER */}
        <div className="text-center text-sm text-soft">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-400 hover:underline">
            Login
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
