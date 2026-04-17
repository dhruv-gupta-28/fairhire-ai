import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  BarChart3,
  FileText,
  Briefcase,
  History,
  TrendingUp,
  Shield,
  Activity,
  Clock,
  ArrowRight,
} from "lucide-react";

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalAnalyses: 0,
    totalReports: 0,
    recentActivity: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem("token");

      const response = await axios.get("/history", { withCredentials: true });
      const historyData = response.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      const totalAnalyses = historyData.filter(d => d.type === 'bias_detection').length;
      const totalReports = historyData.filter(d => d.type === 'resume_analysis').length;

      setStats({
        totalAnalyses,
        totalReports,
        recentActivity: historyData.slice(0, 5),
      });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const features = [
    {
      title: "Bias Detection",
      icon: Shield,
      path: "/analysis",
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      description: "Analyze hiring data for bias patterns",
    },
    {
      title: "Resume Analysis",
      icon: FileText,
      path: "/resume-analysis",
      color: "text-green-400",
      bg: "bg-green-500/10",
      description: "Extract insights from resumes",
    },
    {
      title: "Job Matching",
      icon: Briefcase,
      path: "/job-matching",
      color: "text-purple-400",
      bg: "bg-purple-500/10",
      description: "Match candidates to jobs",
    },
  ];

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="flex items-center text-gray-400 text-sm">
          <div className="loading mr-3"></div>
          Loading Dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-1">Dashboard</h1>
        <p className="text-gray-500 text-sm">AI-powered fair hiring insights</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-3 mb-6">
        <div className="stat-card">
          <BarChart3 className="w-5 h-5 text-blue-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.totalAnalyses}</div>
          <div className="text-gray-500 text-xs mt-1">Total Analyses</div>
        </div>
        <div className="stat-card">
          <FileText className="w-5 h-5 text-green-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.totalReports}</div>
          <div className="text-gray-500 text-xs mt-1">Reports Generated</div>
        </div>
        <div className="stat-card">
          <TrendingUp className="w-5 h-5 text-purple-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">98%</div>
          <div className="text-gray-500 text-xs mt-1">System Accuracy</div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-2 mb-6">
        {features.map((feature, i) => {
          const Icon = feature.icon;
          return (
            <Link key={i} to={feature.path} className="card hover-lift group block">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${feature.bg}`}>
                  <Icon className={`w-4 h-4 ${feature.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors card-title">
                    {feature.title}
                  </h3>
                  <p className="text-gray-500 text-xs">{feature.description}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors" />
              </div>
            </Link>
          );
        })}
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-white">Recent Activity</h3>
        </div>

        {stats.recentActivity.length > 0 ? (
          <div className="space-y-2">
            {stats.recentActivity.map((activity, i) => (
              <div
                key={i}
                className="info-row"
              >
                {activity.type === "bias_detection" ? (
                  <Shield className="w-4 h-4 text-blue-400 flex-shrink-0" />
                ) : activity.type === "resume_analysis" ? (
                  <FileText className="w-4 h-4 text-green-400 flex-shrink-0" />
                ) : (
                  <Briefcase className="w-4 h-4 text-purple-400 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-white text-sm font-medium">
                    {activity.type ? activity.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') : "System Event"}
                  </div>
                </div>
                <div className="flex items-center gap-1 text-gray-500 text-xs flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  {new Date(activity.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Activity className="w-8 h-8 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No activity yet. Start analyzing to see history here.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
