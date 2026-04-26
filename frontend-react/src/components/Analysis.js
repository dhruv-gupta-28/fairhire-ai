import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import {
  Upload,
  AlertCircle,
  CheckCircle,
  Download,
  BarChart3,
  ArrowRight,
  FileSpreadsheet,
  Sparkles,
  RotateCcw,
} from "lucide-react";
import GuidedStepper from "./GuidedStepper";
import FeatureImportance from "./FeatureImportance";

const STEP_UPLOAD = 1;
const STEP_ANALYZE = 2;
const STEP_RESULTS = 3;
const STEP_DOWNLOAD = 4;
const STORAGE_KEY = "fairhire.analysis.flow";

const normalizeScore = (value) => {
  const parsed =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number(value)
        : NaN;

  return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : null;
};

const normalizeAnalysisResults = (data) => {
  const normalizedScore =
    normalizeScore(data?.fairness_score) ??
    normalizeScore(data?.final_score) ??
    normalizeScore(data?.before?.fairness_score) ??
    normalizeScore(data?.bias_summary?.fairness_score);

  return {
    ...data,
    fairness_score: normalizedScore,
    summary: data?.detailed_summary || data?.summary || "",
    bias_level:
      data?.bias_level ??
      data?.before?.bias_level ??
      data?.bias_summary?.bias_level ??
      null,
  };
};

const Analysis = () => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [step, setStep] = useState(STEP_UPLOAD);
  const [highestStep, setHighestStep] = useState(STEP_UPLOAD);

  const steps = useMemo(
    () => [
      {
        id: "upload",
        label: "Upload Dataset",
        hint: "Choose the CSV file to audit.",
      },
      {
        id: "analyze",
        label: "Run Analysis",
        hint: "Launch fairness detection.",
      },
      {
        id: "results",
        label: "Review Results",
        hint: "Inspect score, summary, and bias breakdown.",
      },
      {
        id: "download",
        label: "Download Report",
        hint: "Export the analysis PDF.",
      },
    ],
    []
  );

  const getAllowedStep = useCallback((hasSelectedFile, hasAnalysisResults) => {
    if (hasAnalysisResults) {
      return STEP_DOWNLOAD;
    }

    if (hasSelectedFile) {
      return STEP_ANALYZE;
    }

    return STEP_UPLOAD;
  }, []);

  const unlockStep = (targetStep) => {
    setHighestStep((current) => Math.min(STEP_DOWNLOAD, Math.max(current, targetStep)));
  };

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
    setFileName(selectedFile.name);
    setError("");
    setResults(null);
    setStep(STEP_ANALYZE);
    setHighestStep(STEP_ANALYZE);
  }, []);

  useEffect(() => {
    try {
      const savedFlow = localStorage.getItem(STORAGE_KEY);
      if (!savedFlow) return;

      const parsed = JSON.parse(savedFlow);
      const restoredResults = parsed?.results
        ? normalizeAnalysisResults(parsed.results)
        : null;
      const allowedStep = getAllowedStep(false, Boolean(restoredResults));
      const savedStep = Number(parsed?.step) || STEP_UPLOAD;
      const nextStep = Math.min(savedStep, allowedStep);

      setResults(restoredResults);
      setFileName(restoredResults ? parsed?.fileName || "" : "");
      setHighestStep(allowedStep);
      setStep(nextStep);
    } catch (storageError) {
      console.error("Failed to restore guided flow state:", storageError);
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [getAllowedStep]);

  useEffect(() => {
    const allowedStep = getAllowedStep(Boolean(file), Boolean(results));

    setHighestStep((current) => Math.min(STEP_DOWNLOAD, Math.max(current, allowedStep)));
    setStep((current) => Math.min(current, allowedStep));
  }, [file, results, getAllowedStep]);

  useEffect(() => {
    const persistableResults = results || null;
    const allowedStep = getAllowedStep(Boolean(file), Boolean(results));
    const persistedStep = Math.min(step, allowedStep);

    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        step: persistableResults ? persistedStep : STEP_UPLOAD,
        fileName: file?.name || fileName || "",
        results: persistableResults,
      })
    );
  }, [file, fileName, results, step, getAllowedStep]);

  const resetFlow = useCallback(() => {
    setFile(null);
    setFileName("");
    setLoading(false);
    setReportLoading(false);
    setResults(null);
    setError("");
    setStep(STEP_UPLOAD);
    setHighestStep(STEP_UPLOAD);
    localStorage.removeItem(STORAGE_KEY);
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

      if (response.data.error || response.data.failed) {
        throw new Error(response.data.error || "Analysis failed on backend");
      }

      setResults(normalizeAnalysisResults(response.data));
      unlockStep(STEP_RESULTS);
      setStep(STEP_RESULTS);
    } catch (requestError) {
      const errorMessage =
        requestError.response?.data?.error ||
        requestError.message ||
        "Analysis failed.";
      setError(errorMessage);
      console.error("Analysis error details:", requestError);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!results) return;

    setReportLoading(true);
    setError("");

    try {
      const response = await axios.post("/report", results, {
        responseType: "blob",
      });

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "fairhire_report.pdf";
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setError("Report generation failed.");
      console.error("Report error details:", requestError);
    } finally {
      setReportLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  const biasBreakdownAvailable =
    results &&
    [
      results.gender_bias,
      results.age_bias,
      results.race_bias,
      results.education_bias,
    ].some((group) => group && Object.keys(group).length > 0);

  const canAccessAnalyze = Boolean(file);
  const canAccessResults = Boolean(results);
  const canAccessDownload = Boolean(results);
  const resolvedHighestStep = getAllowedStep(Boolean(file), Boolean(results));
  const currentFileName = file?.name || fileName;

  return (
    <div className="fade-in">
      <div className="mb-5 guided-page-header">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">
            AI-Powered Fair Hiring Analysis
          </h1>
          <p className="text-gray-500 text-sm">
            Follow the guided flow to upload data, run the audit, review
            insights, and export the final report.
          </p>
        </div>

        <button
          type="button"
          className="btn-secondary flex items-center gap-2 text-sm"
          onClick={resetFlow}
        >
          <RotateCcw className="w-4 h-4" />
          Start New Analysis
        </button>
      </div>

      <GuidedStepper
        steps={steps}
        currentStep={step}
        highestStep={Math.max(highestStep, resolvedHighestStep)}
        onStepChange={(targetStep) => {
          if (targetStep <= resolvedHighestStep) {
            setStep(targetStep);
          }
        }}
      />

      {error && (
        <div className="mb-5 bg-red-900/30 border border-red-500/30 text-red-300 px-3 py-2 rounded-lg flex items-center text-xs">
          <AlertCircle className="mr-2 w-4 h-4 flex-shrink-0" /> {error}
        </div>
      )}

      {step === STEP_UPLOAD && (
        <div className="card">
          <div
            {...getRootProps()}
            className={`p-10 border-2 border-dashed rounded-lg cursor-pointer transition-all ${
              isDragActive
                ? "border-blue-400 bg-blue-500/5"
                : "border-gray-800 hover:border-gray-600"
            }`}
          >
            <input {...getInputProps()} />
            <div className="text-center">
              <Upload className="mx-auto mb-3 w-10 h-10 text-gray-600" />
              {file ? (
                <p className="text-green-400 text-sm font-medium">
                  Uploaded: {file.name}
                </p>
              ) : (
                <>
                  <p className="text-gray-300 text-sm mb-1">
                    Drop your CSV file here
                  </p>
                  <p className="text-gray-600 text-xs">
                    Start the flow with a hiring dataset in CSV format.
                  </p>
                </>
              )}
            </div>
          </div>

          <div className="guided-panel-footer mt-5">
            <div className="guided-panel-copy">
              <FileSpreadsheet className="w-4 h-4 text-blue-400" />
              <span className="text-gray-400 text-xs">
                The next step unlocks once a valid CSV is selected.
              </span>
            </div>

            <button
              type="button"
              className="btn-primary disabled:opacity-50 flex items-center gap-2 text-sm"
              disabled={!canAccessAnalyze}
              onClick={() => setStep(STEP_ANALYZE)}
            >
              Continue
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {step === STEP_ANALYZE && (
        <div className="card">
          <div className="guided-panel-header">
            <div>
              <h2 className="section-heading text-sm mb-1">
                Step 2: Run Analysis
              </h2>
              <p className="text-gray-500 text-xs">
                Launch the fairness engine once the dataset is ready.
              </p>
            </div>
            {currentFileName && (
              <div className="guided-panel-file">
                <FileSpreadsheet className="w-4 h-4 text-blue-400" />
                <span>{currentFileName}</span>
              </div>
            )}
          </div>

          {loading ? (
            <div className="guided-analysis-loader">
              <div className="guided-loader-row">
                <div className="loading"></div>
                <span className="text-sm font-semibold text-white">
                  Running fairness analysis
                </span>
              </div>
              <div className="guided-loader-steps">
                <div className="guided-loader-step active">
                  Validating upload and parsing columns
                </div>
                <div className="guided-loader-step active">
                  Measuring bias and fairness gaps
                </div>
                <div className="guided-loader-step active">
                  Preparing recommendations and report data
                </div>
              </div>
            </div>
          ) : (
            <div className="guided-panel-body">
              <div className="guided-panel-metric">
                <span className="guided-panel-metric-label">Upload Status</span>
                <span className="guided-panel-metric-value">
                  {canAccessAnalyze ? "Ready" : "Pending"}
                </span>
              </div>
              <div className="guided-panel-metric">
                <span className="guided-panel-metric-label">Next Outcome</span>
                <span className="guided-panel-metric-value">
                  Score, bias breakdown, recommendations
                </span>
              </div>
            </div>
          )}

          <div className="guided-panel-footer">
            <button
              type="button"
              className="btn-secondary flex items-center gap-2 text-sm"
              onClick={() => setStep(STEP_UPLOAD)}
            >
              Back to Upload
            </button>

            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!canAccessAnalyze || loading}
              className="btn-primary disabled:opacity-50 flex items-center gap-2 text-sm"
              title={
                canAccessAnalyze
                  ? "Run the bias analysis"
                  : "Upload a CSV file to unlock analysis"
              }
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
          </div>
        </div>
      )}

      {step === STEP_RESULTS && results && (
        <>
          <div className="mb-5 bg-green-500/10 border border-green-500/20 text-green-400 px-3 py-2 rounded-lg flex items-center justify-center text-xs">
            <CheckCircle className="mr-2 w-4 h-4" /> Analysis completed
            successfully
          </div>

          <div className="grid grid-2 gap-4">
            <div className="stat-card flex flex-col items-center justify-center py-6">
              <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                Fairness Score
              </h2>
              {results.fairness_score !== undefined &&
              results.fairness_score !== null ? (
                <>
                  <div
                    className={`text-4xl font-bold ${getScoreColor(
                      results.fairness_score
                    )}`}
                  >
                    {results.fairness_score}
                  </div>
                  <div className="text-gray-600 text-xs mt-1">/100</div>
                  {results.bias_level && (
                    <div className="text-gray-500 text-xs mt-3 px-2 py-1 bg-gray-800/50 rounded">
                      {results.bias_level}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-gray-500 text-sm">
                  N/A
                  <div className="text-xs mt-2 text-gray-600">
                    Score unavailable
                  </div>
                </div>
              )}
            </div>

            <div className="card">
              <h3 className="section-heading text-sm">Run Summary</h3>
              <div className="space-y-2">
                <div className="info-row">
                  <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span className="text-gray-300 text-xs">
                    Review the score, bias level, and recommendations before
                    exporting the report.
                  </span>
                </div>
                {results.summary ? (
                  <p className="text-gray-400 text-xs leading-relaxed">
                    {results.summary}
                  </p>
                ) : (
                  <p className="text-gray-500 text-xs">
                    No AI summary was returned for this dataset.
                  </p>
                )}
              </div>
            </div>

            {results.impact_statement && (
              <div className="card">
                <h3 className="section-heading text-sm">Impact Statement</h3>
                <p className="text-gray-400 text-xs leading-relaxed">
                  {results.impact_statement}
                </p>
              </div>
            )}

            {biasBreakdownAvailable && (
              <div className="card">
                <h3 className="section-heading text-sm">Bias Breakdown</h3>
                <div className="space-y-2">
                  {results.gender_bias &&
                    Object.entries(results.gender_bias).map(([key, value]) => (
                      <div key={`gender-${key}`} className="info-row">
                        <span className="text-gray-400 text-xs flex-1">
                          Gender: {key}
                        </span>
                        <span className="text-white text-xs font-mono">
                          {(value * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  {results.age_bias &&
                    Object.entries(results.age_bias).map(([key, value]) => (
                      <div key={`age-${key}`} className="info-row">
                        <span className="text-gray-400 text-xs flex-1">
                          Age: {key}
                        </span>
                        <span className="text-white text-xs font-mono">
                          {(value * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  {results.race_bias &&
                    Object.entries(results.race_bias).map(([key, value]) => (
                      <div key={`race-${key}`} className="info-row">
                        <span className="text-gray-400 text-xs flex-1">
                          Race: {key}
                        </span>
                        <span className="text-white text-xs font-mono">
                          {(value * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  {results.education_bias &&
                    Object.entries(results.education_bias).map(
                      ([key, value]) => (
                        <div key={`education-${key}`} className="info-row">
                          <span className="text-gray-400 text-xs flex-1">
                            Education: {key}
                          </span>
                          <span className="text-white text-xs font-mono">
                            {(value * 100).toFixed(1)}%
                          </span>
                        </div>
                      )
                    )}
                </div>
              </div>
            )}

            <FeatureImportance
              shapSummary={results.shap_summary}
              biasByFeature={results.bias_by_feature}
              selectionRates={results.selection_rates}
              fairnessScore={results.fairness_score}
              biasLevel={results.bias_level}
            />

            {results.recommendations && results.recommendations.length > 0 && (
              <div className="card">
                <h3 className="section-heading text-sm">Recommendations</h3>
                <div className="space-y-2">
                  {results.recommendations.map((recommendation, index) => (
                    <div key={index} className="info-row">
                      <CheckCircle className="text-green-400 w-3.5 h-3.5 flex-shrink-0" />
                      <span className="text-gray-300 text-xs">
                        {recommendation}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="guided-panel-footer mt-5">
            <button
              type="button"
              className="btn-secondary flex items-center gap-2 text-sm"
              onClick={() => setStep(STEP_ANALYZE)}
            >
              Back to Analysis
            </button>

            <button
              type="button"
              className="btn-primary flex items-center gap-2 text-sm"
              disabled={!canAccessResults}
              onClick={() => {
                if (canAccessDownload) {
                  unlockStep(STEP_DOWNLOAD);
                  setStep(STEP_DOWNLOAD);
                }
              }}
            >
              Continue to Download
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </>
      )}

      {step === STEP_DOWNLOAD && results && (
        <div className="card">
          <div className="guided-panel-header">
            <div>
              <h2 className="section-heading text-sm mb-1">
                Step 4: Download Report
              </h2>
              <p className="text-gray-500 text-xs">
                Export the current results as a PDF for sharing or demo review.
              </p>
            </div>

            {results.fairness_score !== null && results.fairness_score !== undefined && (
              <div className="guided-panel-score">
                Fairness Score: {results.fairness_score}/100
              </div>
            )}
          </div>

          <div className="guided-download-card">
            <div className="guided-download-copy">
              <Download className="w-5 h-5 text-blue-400" />
              <div>
                <h3 className="text-sm font-semibold text-white mb-1">
                  Ready to export
                </h3>
                <p className="text-gray-400 text-xs">
                  The report includes the fairness score, summary, and
                  recommendations shown in Step 3.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleGenerateReport}
              disabled={!canAccessDownload || reportLoading}
              className="btn-primary disabled:opacity-50 flex items-center gap-2 text-sm"
              title={
                canAccessDownload
                  ? "Download the PDF report"
                  : "Run an analysis to unlock the report"
              }
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
          </div>

          <div className="guided-panel-footer mt-5">
            <button
              type="button"
              className="btn-secondary flex items-center gap-2 text-sm"
              onClick={() => setStep(STEP_RESULTS)}
            >
              Back to Results
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analysis;
