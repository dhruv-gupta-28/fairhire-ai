import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  BarChart3,
  FileText,
  Briefcase,
  Calendar,
  Clock,
  AlertCircle,
  FileDown,
} from "lucide-react";

const History = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const token = localStorage.getItem("token");

      const res = await axios.get("/history", {
        headers: { Authorization: `Bearer ${token}` },
      });

      setHistory(res.data);
    } catch (error) {
      setError("Failed to load history.");
    } finally {
      setLoading(false);
    }
  };

  const getFairnessColor = (score) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  const renderIcon = (type) => {
    switch (type) {
      case "bias_detection":
        return <div className="p-2 bg-blue-500/10 rounded-lg"><BarChart3 className="w-4 h-4 text-blue-400" /></div>;
      case "resume_analysis":
        return <div className="p-2 bg-purple-500/10 rounded-lg"><FileText className="w-4 h-4 text-purple-400" /></div>;
      case "job_match":
        return <div className="p-2 bg-green-500/10 rounded-lg"><Briefcase className="w-4 h-4 text-green-400" /></div>;
      default:
        return <div className="p-2 bg-gray-500/10 rounded-lg"><FileText className="w-4 h-4 text-gray-400" /></div>;
    }
  };

  const renderTitle = (type) => {
    switch (type) {
      case "bias_detection":
        return "Bias Analysis";
      case "resume_analysis":
        return "Resume Analysis";
      case "job_match":
        return "Job Matching";
      default:
        return "Activity Log";
    }
  };

  const renderResult = (item) => {
    if (item.type === "bias_detection") {
      const score = item.output_results?.fairness_score || 0;
      return (
        <div className={`text-xl font-bold ${getFairnessColor(score)}`}>
          {score}
          <span className="text-gray-600 text-xs font-normal">/100</span>
        </div>
      );
    } else if (item.type === "resume_analysis") {
      const score = item.output_results?.resume_score || 0;
      return (
        <div className="text-xl font-bold text-purple-400">
          {score}
          <span className="text-gray-600 text-xs font-normal"> pts</span>
        </div>
      );
    } else if (item.type === "job_match") {
      const jobs = item.output_results?.jobs_found || 0;
      const score = item.output_results?.top_match_score || 0;
      return (
        <div className="text-right">
            <div className="text-sm font-bold text-green-400">{jobs} Jobs Found</div>
            <div className="text-xs text-gray-500">Top Match: {score}%</div>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="flex items-center text-gray-400 text-sm">
          <div className="loading mr-3"></div>
          Loading History...
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-white mb-1">History</h1>
        <p className="text-gray-500 text-sm">View your past activities</p>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-500/30 text-red-300 px-3 py-2 rounded-lg mb-4 flex items-center text-xs">
          <AlertCircle className="mr-2 w-4 h-4" /> {error}
        </div>
      )}

      {/* Activity Timeline */}
      <div className="space-y-3">
        {history.length > 0 ? (
          history.map((item, i) => (
            <div key={i} className="card hover-lift">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {renderIcon(item.type)}
                  <div>
                    <h3 className="text-sm font-semibold text-white">{renderTitle(item.type)}</h3>
                    <div className="flex items-center gap-3 text-gray-500 text-xs mt-0.5">
                      {item.input_metadata?.filename && (
                        <span className="truncate max-w-[150px]">{item.input_metadata.filename}</span>
                      )}
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(item.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
                {renderResult(item)}
              </div>
            </div>
          ))
        ) : (
          <div className="card text-center py-10 border-dashed">
            <FileDown className="w-8 h-8 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No activity yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
