import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import { Upload, AlertCircle, CheckCircle, Download, BarChart3 } from "lucide-react";

const Analysis = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  const onDrop = useCallback((acceptedFiles) => {
    const selectedFile = acceptedFiles[0];

    if (!selectedFile) {
      setError("Please select a file");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".csv")) {
      setError("Please upload a valid .csv file");
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
      "text/csv": [".csv"],
      "application/vnd.ms-excel": [".csv"],
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
      const response = await axios.post("/analyze", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setResults(response.data);
    } catch (error) {
      setError(error.response?.data?.error || "Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!results) return;

    setReportLoading(true);

    try {
      const response = await axios.post("/report", results, {
        responseType: "blob"
      });

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "fairhire_report.pdf";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setError("Report generation failed.");
    } finally {
      setReportLoading(false);
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
        <h1 className="text-2xl font-bold text-white mb-1">Bias Analysis</h1>
        <p className="text-gray-500 text-sm">Upload hiring data to detect bias patterns</p>
      </div>

      {/* Upload Card */}
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
                <p className="text-gray-300 text-sm mb-1">Drop your CSV file here</p>
                <p className="text-gray-600 text-xs">or click to browse</p>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 bg-red-900/30 border border-red-500/30 text-red-300 px-3 py-2 rounded-lg flex items-center text-xs">
            <AlertCircle className="mr-2 w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button
            onClick={handleAnalyze}
            disabled={!file || loading}
            className="btn-primary disabled:opacity-50 flex items-center gap-2 text-sm"
          >
            {loading ? (
              <>
                <div className="loading"></div>
                Analyzing...
              </>
            ) : (
              <>
                <BarChart3 className="w-4 h-4" />
                Run Analysis
              </>
            )}
          </button>

          {results && (
            <button
              onClick={handleGenerateReport}
              disabled={reportLoading}
              className="btn-secondary disabled:opacity-50 flex items-center gap-2 text-sm"
            >
              {reportLoading ? (
                <>
                  <div className="loading"></div>
                  Generating...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Download Report
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Success Banner */}
      {results && (
        <div className="mb-5 bg-green-500/10 border border-green-500/20 text-green-400 px-3 py-2 rounded-lg flex items-center justify-center text-xs">
          <CheckCircle className="mr-2 w-4 h-4" /> Analysis completed successfully
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="grid grid-2 gap-4">
          {/* Score Card */}
          <div className="stat-card flex flex-col items-center justify-center py-6">
            <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Fairness Score
            </h2>
            <div className={`text-4xl font-bold ${getScoreColor(results.fairness_score)}`}>
              {results.fairness_score}
            </div>
            <div className="text-gray-600 text-xs mt-1">/100</div>
          </div>

          {/* AI Summary */}
          {results.summary && (
            <div className="card">
              <h3 className="section-heading text-sm">AI Summary</h3>
              <div className="text-gray-400 text-xs leading-relaxed space-y-2">
                {results.summary.split('\n').filter(p => p.trim() !== '').map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            </div>
          )}

          {/* Bias Breakdown */}
          {(results.gender_bias || results.age_bias || results.race_bias) && (
            <div className="card">
              <h3 className="section-heading text-sm">Bias Breakdown</h3>
              <div className="space-y-2">
                {results.gender_bias && Object.entries(results.gender_bias).map(([k, v]) => (
                  <div key={k} className="info-row">
                    <span className="text-gray-400 text-xs flex-1">Gender: {k}</span>
                    <span className="text-white text-xs font-mono">{(v * 100).toFixed(1)}%</span>
                  </div>
                ))}
                {results.age_bias && Object.entries(results.age_bias).map(([k, v]) => (
                  <div key={k} className="info-row">
                    <span className="text-gray-400 text-xs flex-1">Age: {k}</span>
                    <span className="text-white text-xs font-mono">{(v * 100).toFixed(1)}%</span>
                  </div>
                ))}
                {results.race_bias && Object.entries(results.race_bias).map(([k, v]) => (
                  <div key={k} className="info-row">
                    <span className="text-gray-400 text-xs flex-1">Race: {k}</span>
                    <span className="text-white text-xs font-mono">{(v * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {results.recommendations && (
            <div className="card">
              <h3 className="section-heading text-sm">Recommendations</h3>
              <div className="space-y-2">
                {results.recommendations.map((r, i) => (
                  <div key={i} className="info-row">
                    <CheckCircle className="text-green-400 w-3.5 h-3.5 flex-shrink-0" />
                    <span className="text-gray-300 text-xs">{r}</span>
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

export default Analysis;
