import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import {
  Upload,
  User,
  Mail,
  Phone,
  Award,
  CheckCircle,
  AlertCircle,
  FileText,
} from "lucide-react";

const ResumeAnalysis = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  const onDrop = useCallback((acceptedFiles) => {
    const selectedFile = acceptedFiles[0];

    if (!selectedFile) return;

    const allowedExtensions = [".pdf", ".docx"];
    const fileExt = selectedFile.name
      .toLowerCase()
      .substring(selectedFile.name.lastIndexOf("."));

    if (!allowedExtensions.includes(fileExt)) {
      setError("Upload a valid PDF or DOCX file");
      return;
    }

    setFile(selectedFile);
    setError("");
    setResults(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
  });

  const handleAnalyze = async () => {
    if (!file) return;

    setLoading(true);
    setError("");
    setResults(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("/resume/analyze", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setResults(response.data);
    } catch (error) {
      setError("Resume analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-white mb-1">Resume Analysis</h1>
        <p className="text-gray-500 text-sm">Extract insights from PDF and DOCX resumes</p>
      </div>

      {/* Upload */}
      <div className="card mb-5">
        <div
          {...getRootProps()}
          className={`p-8 border-2 border-dashed rounded-lg cursor-pointer transition-all ${
            isDragActive
              ? "border-blue-400 bg-blue-500/5"
              : "border-gray-800 hover:border-gray-600"
          }`}
        >
          <input {...getInputProps()} />
          <div className="text-center">
            <Upload className="mx-auto mb-3 w-8 h-8 text-gray-600" />
            {file ? (
              <p className="text-green-400 text-sm font-medium">✓ {file.name}</p>
            ) : (
              <>
                <p className="text-gray-300 text-sm mb-1">Drop your resume here</p>
                <p className="text-gray-600 text-xs">Supports PDF and DOCX</p>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 bg-red-900/30 border border-red-500/30 text-red-300 px-3 py-2 rounded-lg flex items-center text-xs">
            <AlertCircle className="mr-2 w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        <div className="mt-5">
          <button
            onClick={handleAnalyze}
            className="btn-primary disabled:opacity-50 flex items-center gap-2 text-sm"
            disabled={!file || loading}
          >
            {loading ? (
              <>
                <div className="loading"></div>
                Analyzing...
              </>
            ) : (
              <>
                <FileText className="w-4 h-4" />
                Analyze Resume
              </>
            )}
          </button>
        </div>
      </div>

      {/* Success */}
      {results && (
        <div className="mb-5 bg-green-500/10 border border-green-500/20 text-green-400 px-3 py-2 rounded-lg flex items-center justify-center text-xs">
          <CheckCircle className="mr-2 w-4 h-4" /> Resume analyzed successfully
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="grid grid-2 gap-4">
          {/* Score */}
          <div className="stat-card flex flex-col items-center justify-center py-6">
            <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Resume Score
            </h2>
            <div className={`text-4xl font-bold ${getScoreColor(results.resume_score)}`}>
              {results.resume_score}
            </div>
            <div className="text-gray-600 text-xs mt-1">/100</div>
          </div>

          {/* AI Summary */}
          {results.ai_summary && (
            <div className="card flex flex-col justify-center">
              <h3 className="section-heading text-sm">AI Summary</h3>
              <div className="text-gray-400 text-xs leading-relaxed space-y-2">
                {results.ai_summary.split('\n').filter(p => p.trim() !== '').map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Info */}
          <div className="card">
            <h3 className="section-heading text-sm">Extracted Information</h3>
            <div className="space-y-2">
              <div className="info-row">
                <User className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <span className="text-gray-300 text-xs">{results.name || "Not found"}</span>
              </div>
              <div className="info-row">
                <Mail className="w-4 h-4 text-green-400 flex-shrink-0" />
                <span className="text-gray-300 text-xs">{results.email || "Not found"}</span>
              </div>
              <div className="info-row">
                <Phone className="w-4 h-4 text-purple-400 flex-shrink-0" />
                <span className="text-gray-300 text-xs">{results.phone || "Not found"}</span>
              </div>
              <div className="info-row">
                <Award className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                <span className="text-gray-300 text-xs">{results.experience_years || 0} years experience</span>
              </div>
            </div>
          </div>

          {/* Skills */}
          {results.skills && results.skills.length > 0 && (
            <div className="card">
              <h3 className="section-heading text-sm">Skills Detected</h3>
              <div className="flex flex-wrap gap-1.5">
                {results.skills.map((skill, i) => (
                  <span key={i} className="skill-tag">{skill}</span>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {results.recommendations && results.recommendations.length > 0 && (
            <div className="card">
              <h3 className="section-heading text-sm">Recommendations</h3>
              <div className="space-y-2">
                {results.recommendations.map((rec, i) => (
                  <div key={i} className="info-row">
                    <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
                    <span className="text-gray-300 text-xs">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ResumeAnalysis;
