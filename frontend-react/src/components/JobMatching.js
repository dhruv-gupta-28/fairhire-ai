import React, { useState } from "react";
import axios from "axios";
import { Target, ExternalLink, MapPin, DollarSign, AlertCircle, UploadCloud, Briefcase } from "lucide-react";

const JobMatching = () => {
  const [jobSearch, setJobSearch] = useState({
    location: "us",
    limit: 5,
  });
  const [file, setFile] = useState(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [jobError, setJobError] = useState("");
  const [globalMatchScore, setGlobalMatchScore] = useState(null);

  const handleJobSearchChange = (e) => {
    setJobSearch({
      ...jobSearch,
      [e.target.name]: e.target.value,
    });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const validTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ];
      if (!validTypes.includes(selectedFile.type)) {
        setJobError("Please upload a valid PDF or DOCX file.");
        setFile(null);
        return;
      }
      setJobError("");
      setFile(selectedFile);
    }
  };

  const handleFetchJobs = async () => {
    if (!file) {
      setJobError("Please upload a resume file before matching jobs.");
      return;
    }

    setJobLoading(true);
    setJobError("");
    setJobs([]);
    setGlobalMatchScore(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("location", jobSearch.location);
    formData.append("limit", jobSearch.limit);

    try {
      const token = localStorage.getItem("token");

      const response = await axios.post("/job/match", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
      });

      setJobs(response.data.jobs || []);
      setGlobalMatchScore(response.data.match_score);
    } catch (error) {
      if (error.response?.data?.error) {
        setJobError(error.response.data.error);
      } else {
        setJobError("Failed to fetch jobs. Something went wrong.");
      }
    } finally {
      setJobLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score > 70) return "text-green-400";
    if (score > 45) return "text-yellow-400";
    return "text-red-400";
  };

  const getScoreBg = (score) => {
    if (score > 70) return "bg-green-500/10 border-green-500/20";
    if (score > 45) return "bg-yellow-500/10 border-yellow-500/20";
    return "bg-red-500/10 border-red-500/20";
  };

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-white mb-1">Job Matching</h1>
        <p className="text-gray-500 text-sm">Upload your resume to find matching positions</p>
      </div>

      {/* Upload & Options */}
      <div className="card mb-5">
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Resume (PDF, DOCX)</label>
          <div className="border border-gray-800 rounded-lg p-3 bg-[#0a0a0a] hover:border-gray-700 transition-colors">
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileChange}
              className="text-xs text-gray-400 w-full file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-blue-600 file:text-white hover:file:bg-blue-700 file:cursor-pointer file:transition-colors"
            />
          </div>
          {file && (
            <p className="text-green-400 text-xs mt-1.5 truncate">✓ {file.name}</p>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Location */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Location</label>
            <select
              name="location"
              value={jobSearch.location}
              onChange={handleJobSearchChange}
              className="input-field w-full text-sm"
            >
              <option value="us">🇺🇸 United States</option>
              <option value="gb">🇬🇧 United Kingdom</option>
              <option value="in">🇮🇳 India</option>
              <option value="ca">🇨🇦 Canada</option>
              <option value="au">🇦🇺 Australia</option>
              <option value="de">🇩🇪 Germany</option>
              <option value="remote">🌍 Remote Jobs</option>
              <option value="all">🌐 All Countries</option>
            </select>
          </div>

          {/* Results Count */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Results</label>
            <select
              name="limit"
              value={jobSearch.limit}
              onChange={handleJobSearchChange}
              className="input-field w-full text-sm"
            >
              <option value={3}>3 jobs</option>
              <option value={5}>5 jobs</option>
              <option value={10}>10 jobs</option>
            </select>
          </div>
        </div>

        {jobError && (
          <div className="bg-red-900/30 border border-red-500/30 text-red-300 px-3 py-2 rounded-lg flex items-center mb-4 text-xs">
            <AlertCircle className="mr-2 w-4 h-4 flex-shrink-0" />
            {jobError}
          </div>
        )}

        <button
          onClick={handleFetchJobs}
          disabled={jobLoading || !file}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm"
        >
          {jobLoading ? (
            <>
              <div className="loading"></div>
              Matching...
            </>
          ) : (
            <>
              <UploadCloud className="w-4 h-4" />
              Match Jobs
            </>
          )}
        </button>
      </div>

      {/* Global Match Score */}
      {globalMatchScore !== null && globalMatchScore > 0 && (
        <div className={`mb-5 p-3 rounded-lg border text-center ${getScoreBg(globalMatchScore)}`}>
          <span className="text-xs text-gray-400">Best Match Score: </span>
          <span className={`text-lg font-bold ${getScoreColor(globalMatchScore)}`}>{globalMatchScore}%</span>
        </div>
      )}

      {/* Job Results */}
      {jobs.length > 0 && (
        <div className="space-y-3">
          <h3 className="section-heading flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-blue-400" />
            {jobs.length} Matching Positions
          </h3>

          {jobs.map((job, i) => (
            <div key={i} className="card hover-lift">
              <div className="flex flex-col sm:flex-row justify-between sm:items-start gap-3">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-white mb-0.5">{job.title}</h4>
                  <p className="text-blue-400 text-xs font-medium">{job.company}</p>

                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {job.location && (
                      <span className="flex items-center gap-1 text-gray-500 text-xs bg-gray-900 px-2 py-0.5 rounded">
                        <MapPin className="w-3 h-3" />
                        {job.location}
                      </span>
                    )}
                    {job.salary_min && (
                      <span className="flex items-center gap-1 text-gray-500 text-xs bg-gray-900 px-2 py-0.5 rounded">
                        <DollarSign className="w-3 h-3" />
                        ${job.salary_min.toLocaleString()} – ${job.salary_max?.toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className={`px-3 py-1.5 rounded border text-center ${getScoreBg(job.match_score)}`}>
                    <div className="text-[10px] text-gray-400 uppercase tracking-wider">Match</div>
                    <div className={`text-sm font-bold ${getScoreColor(job.match_score)}`}>
                      {job.match_score}%
                    </div>
                  </div>
                  <a
                    href={job.apply_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary flex items-center gap-1 text-xs py-2 px-3"
                  >
                    Apply <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              {job.description && (
                <p className="text-gray-400 text-xs mt-3 pt-3 border-t border-gray-800/50 leading-relaxed">
                  {job.description.length > 200 ? `${job.description.substring(0, 200)}...` : job.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {jobs.length === 0 && !jobLoading && !jobError && (
        <div className="card text-center py-12 border-dashed">
          <Target className="w-8 h-8 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Upload your resume and click "Match Jobs" to find positions</p>
        </div>
      )}
    </div>
  );
};

export default JobMatching;
