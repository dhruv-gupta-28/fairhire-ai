import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  User,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Save,
  AlertCircle,
  CheckCircle,
  Link,
  FileText,
  Edit3,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const Profile = () => {
  const { logout } = useAuth();
  const [profile, setProfile] = useState({
    name: "",
    age: "",
    gender: "",
    phone: "",
    location: "",
    bio: "",
    skills: "",
    linkedin: "",
    github: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await axios.get("/profile", {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = response.data;
      setProfile({
        name: data.name || "",
        age: data.age || "",
        gender: data.gender || "",
        phone: data.phone || "",
        location: data.location || "",
        bio: data.bio || "",
        skills: Array.isArray(data.skills) ? data.skills.join(", ") : data.skills || "",
        linkedin: data.linkedin || "",
        github: data.github || "",
      });
    } catch (err) {
      setError("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
    setError("");
    setSuccess("");
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const token = localStorage.getItem("token");
      const payload = {
        ...profile,
        age: profile.age ? parseInt(profile.age, 10) : null,
        skills: profile.skills
          ? profile.skills.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
      };

      await axios.put("/profile", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setSuccess("Profile updated successfully");
      setEditing(false);
    } catch (err) {
      setError("Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete your profile? This action is permanent!")) return;
    
    setSaving(true);
    setError("");
    try {
      await axios.delete("/profile", { withCredentials: true });
      logout();
    } catch (err) {
      setError("Failed to delete profile");
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="flex items-center text-gray-400 text-sm">
          <div className="loading mr-3"></div>
          Loading Profile...
        </div>
      </div>
    );
  }

  const fields = [
    { key: "name", label: "Full Name", icon: User, placeholder: "John Doe", type: "text" },
    { key: "age", label: "Age", icon: Calendar, placeholder: "28", type: "number" },
    {
      key: "gender", label: "Gender", icon: User, type: "select",
      options: [
        { value: "", label: "Select Gender" },
        { value: "male", label: "Male" },
        { value: "female", label: "Female" },
        { value: "non-binary", label: "Non-Binary" },
        { value: "other", label: "Other" },
        { value: "prefer-not-to-say", label: "Prefer Not to Say" },
      ],
    },
    { key: "phone", label: "Phone", icon: Phone, placeholder: "+1 234 567 890", type: "tel" },
    { key: "location", label: "Location", icon: MapPin, placeholder: "New York, USA", type: "text" },
    { key: "linkedin", label: "LinkedIn", icon: Link, placeholder: "linkedin.com/in/username", type: "url" },
    { key: "github", label: "GitHub", icon: Link, placeholder: "github.com/username", type: "url" },
  ];

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Profile</h1>
          <p className="text-gray-500 text-sm">Manage your personal information</p>
        </div>
        <button
          onClick={() => (editing ? handleSave() : setEditing(true))}
          disabled={saving}
          className={`${editing ? "btn-primary" : "btn-secondary"} flex items-center gap-2 text-sm`}
        >
          {saving ? (
            <>
              <div className="loading"></div>
              Saving...
            </>
          ) : editing ? (
            <>
              <Save className="w-4 h-4" />
              Save Changes
            </>
          ) : (
            <>
              <Edit3 className="w-4 h-4" />
              Edit Profile
            </>
          )}
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-900/30 border border-red-500/30 text-red-300 px-3 py-2 rounded-lg flex items-center mb-4 text-xs">
          <AlertCircle className="mr-2 w-4 h-4 flex-shrink-0" /> {error}
        </div>
      )}
      {success && (
        <div className="bg-green-500/10 border border-green-500/20 text-green-400 px-3 py-2 rounded-lg flex items-center mb-4 text-xs">
          <CheckCircle className="mr-2 w-4 h-4 flex-shrink-0" /> {success}
        </div>
      )}

      {/* Profile Avatar */}
      <div className="card mb-5 flex items-center gap-4">
        <div className="w-14 h-14 bg-blue-600/20 rounded-full flex items-center justify-center flex-shrink-0">
          <User className="w-7 h-7 text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-semibold text-white truncate">
            {profile.name || "Unnamed User"}
          </h2>
          <p className="text-gray-500 text-xs">
            {profile.location || "No location set"} • {profile.gender || "Gender not set"}
          </p>
        </div>
        {profile.age && (
          <div className="stat-card px-4 py-2 flex-shrink-0">
            <div className="text-lg font-bold text-white text-center">{profile.age}</div>
            <div className="text-gray-500 text-[10px] uppercase tracking-wider">Age</div>
          </div>
        )}
      </div>

      {/* Fields */}
      <div className="grid grid-2 gap-4 mb-5">
        {fields.map((field) => {
          const Icon = field.icon;
          return (
            <div key={field.key} className="card">
              <label className="flex items-center gap-2 text-xs font-medium text-gray-400 mb-2">
                <Icon className="w-3.5 h-3.5" />
                {field.label}
              </label>
              {editing ? (
                field.type === "select" ? (
                  <select
                    name={field.key}
                    value={profile[field.key]}
                    onChange={handleChange}
                    className="input-field w-full text-sm"
                  >
                    {field.options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type}
                    name={field.key}
                    value={profile[field.key]}
                    onChange={handleChange}
                    placeholder={field.placeholder}
                    className="input-field w-full text-sm"
                  />
                )
              ) : (
                <div className="text-white text-sm py-2">
                  {profile[field.key] || (
                    <span className="text-gray-600 italic text-xs">Not set</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bio */}
      <div className="card mb-5">
        <label className="flex items-center gap-2 text-xs font-medium text-gray-400 mb-2">
          <FileText className="w-3.5 h-3.5" />
          Bio
        </label>
        {editing ? (
          <textarea
            name="bio"
            value={profile.bio}
            onChange={handleChange}
            placeholder="Tell us about yourself..."
            rows={3}
            className="input-field w-full text-sm resize-none"
          />
        ) : (
          <p className="text-white text-sm leading-relaxed">
            {profile.bio || (
              <span className="text-gray-600 italic text-xs">No bio added</span>
            )}
          </p>
        )}
      </div>

      {/* Skills */}
      <div className="card">
        <label className="flex items-center gap-2 text-xs font-medium text-gray-400 mb-2">
          <Mail className="w-3.5 h-3.5" />
          Skills
        </label>
        {editing ? (
          <input
            type="text"
            name="skills"
            value={profile.skills}
            onChange={handleChange}
            placeholder="Python, React, Machine Learning (comma-separated)"
            className="input-field w-full text-sm"
          />
        ) : profile.skills ? (
          <div className="flex flex-wrap gap-1.5">
            {(typeof profile.skills === "string"
              ? profile.skills.split(",").map((s) => s.trim()).filter(Boolean)
              : profile.skills
            ).map((skill, i) => (
              <span key={i} className="skill-tag">{skill}</span>
            ))}
          </div>
        ) : (
          <span className="text-gray-600 italic text-xs">No skills added</span>
        )}
      </div>

      {/* Danger Zone */}
      <div className="card border-red-500/20 bg-red-900/10 mt-5">
        <h3 className="text-red-400 font-semibold mb-2 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" /> Danger Zone
        </h3>
        <p className="text-gray-400 text-xs mb-4">
          Once you delete your profile, all associated history, analysis reports, and personal metrics are permanently destroyed. There is no going back.
        </p>
        <button
          onClick={handleDelete}
          disabled={saving}
          className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg w-full sm:w-auto text-sm transition-colors disabled:opacity-50"
        >
          {saving ? "Processing..." : "Delete Account"}
        </button>
      </div>
    </div>
  );
};

export default Profile;
