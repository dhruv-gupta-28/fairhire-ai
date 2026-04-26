import React, { useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

const formatSignedValue = (value) => {
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded}` : `${rounded}`;
};

const formatPercent = (value) => `${Math.round(value * 1000) / 10}%`;

const FeatureImportance = ({
  shapSummary,
  biasByFeature,
  selectionRates,
  fairnessScore,
  biasLevel,
}) => {
  const hasSHAP =
    shapSummary &&
    shapSummary.feature_impact &&
    Object.keys(shapSummary.feature_impact).length > 0;

  const hasBias = Array.isArray(biasByFeature) && biasByFeature.length > 0;

  const featureData = useMemo(() => {
    if (!hasSHAP) return [];

    return Object.entries(shapSummary.feature_impact)
      .map(([feature, value]) => ({
        feature,
        value: Number(value) || 0,
      }))
      .sort((left, right) => Math.abs(right.value) - Math.abs(left.value))
      .slice(0, 10);
  }, [hasSHAP, shapSummary]);

  const maxFeatureMagnitude = useMemo(() => {
    if (!featureData.length) return 1;
    return (
      Math.max(...featureData.map((item) => Math.abs(item.value)), 0.01) || 1
    );
  }, [featureData]);

  const topPositive = shapSummary?.top_positive_features || [];
  const topNegative = shapSummary?.top_negative_features || [];

  const fallbackData = useMemo(() => {
    if (!hasBias) return [];

    return biasByFeature
      .map((item) => ({
        feature: item.attribute,
        value: Number(item.demographic_parity_gap) || 0,
        severity: item.severity || "INFO",
      }))
      .sort((left, right) => right.value - left.value);
  }, [biasByFeature, hasBias]);

  const fallbackMax = useMemo(() => {
    if (!fallbackData.length) return 1;
    return Math.max(...fallbackData.map((item) => item.value), 0.01) || 1;
  }, [fallbackData]);

  const modeLabel = hasSHAP
    ? "Explainability Mode: SHAP-based"
    : hasBias
      ? "Explainability Mode: Bias-based fallback"
      : "Explainability Mode: Summary only";

  const selectionRateRows = useMemo(() => {
    if (!selectionRates || typeof selectionRates !== "object") return [];

    return Object.entries(selectionRates)
      .filter(([, groups]) => groups && Object.keys(groups).length > 1)
      .slice(0, 3);
  }, [selectionRates]);

  return (
    <div className="card">
      <div className="feature-importance-header">
        <div>
          <h3 className="section-heading text-sm mb-1">Feature Importance</h3>
          <p className="text-gray-500 text-xs">{modeLabel}</p>
        </div>

        <div className="feature-importance-badge">
          <Sparkles className="w-3.5 h-3.5" />
          <span>
            Fairness Score: {fairnessScore ?? "N/A"}{" "}
            {biasLevel ? `· ${biasLevel}` : ""}
          </span>
        </div>
      </div>

      {hasSHAP && (
        <>
          <div className="feature-chart">
            {featureData.map((item) => {
              const isPositive = item.value >= 0;
              const width = `${Math.max(
                8,
                (Math.abs(item.value) / maxFeatureMagnitude) * 100
              )}%`;

              return (
                <div key={item.feature} className="feature-row">
                  <div className="feature-row-copy">
                    <span className="feature-row-name">{item.feature}</span>
                    <span
                      className={`feature-row-value ${
                        isPositive
                          ? "feature-row-value-positive"
                          : "feature-row-value-negative"
                      }`}
                    >
                      {formatSignedValue(item.value)}
                    </span>
                  </div>

                  <div className="feature-bar-shell">
                    <div
                      className={`feature-bar ${
                        isPositive
                          ? "feature-bar-positive"
                          : "feature-bar-negative"
                      }`}
                      style={{ width }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-2 gap-4 mt-4">
            <div className="feature-sidecard">
              <div className="feature-sidecard-title">
                <ArrowUpRight className="w-4 h-4 text-green-400" />
                Top Positive Factors
              </div>
              {topPositive.length ? (
                topPositive.slice(0, 5).map((feature) => (
                  <div key={feature} className="info-row">
                    <span className="text-gray-300 text-xs">{feature}</span>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-xs">
                  Positive factor breakdown is unavailable for this run.
                </p>
              )}
            </div>

            <div className="feature-sidecard">
              <div className="feature-sidecard-title">
                <ArrowDownRight className="w-4 h-4 text-red-400" />
                Top Negative Factors
              </div>
              {topNegative.length ? (
                topNegative.slice(0, 5).map((feature) => (
                  <div key={feature} className="info-row">
                    <span className="text-gray-300 text-xs">{feature}</span>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-xs">
                  Negative factor breakdown is unavailable for this run.
                </p>
              )}
            </div>
          </div>
        </>
      )}

      {!hasSHAP && hasBias && (
        <>
          <div className="feature-fallback-note">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            <span>
              SHAP data was unavailable for this run, so the system is using
              fairness signals to explain which attributes drive risk.
            </span>
          </div>

          <div className="feature-chart">
            {fallbackData.map((item) => (
              <div key={item.feature} className="feature-row">
                <div className="feature-row-copy">
                  <span className="feature-row-name">{item.feature}</span>
                  <span className="feature-row-severity">{item.severity}</span>
                </div>

                <div className="feature-bar-shell">
                  <div
                    className="feature-bar feature-bar-warning"
                    style={{
                      width: `${Math.max(
                        8,
                        (item.value / fallbackMax) * 100
                      )}%`,
                    }}
                  ></div>
                </div>

                <div className="text-gray-400 text-xs mt-2">
                  Demographic parity gap: {item.value.toFixed(3)}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!hasSHAP && !hasBias && (
        <div className="feature-empty-state">
          <BarChart3 className="w-6 h-6 text-gray-600" />
          <div>
            <p className="text-gray-300 text-sm mb-1">
              No feature importance data was generated for this dataset.
            </p>
            <p className="text-gray-500 text-xs">
              The analysis completed, but explainability metrics were not
              available. Try another dataset or rerun the audit.
            </p>
          </div>
        </div>
      )}

      {selectionRateRows.length > 0 && (
        <div className="feature-selection-card">
          <div className="feature-sidecard-title">
            <Activity className="w-4 h-4 text-blue-400" />
            Selection Rate Snapshot
          </div>

          <div className="space-y-3">
            {selectionRateRows.map(([attribute, groups]) => (
              <div key={attribute}>
                <div className="text-gray-400 text-xs uppercase tracking-wider mb-2">
                  {attribute}
                </div>
                <div className="space-y-2">
                  {Object.entries(groups).map(([group, value]) => (
                    <div key={`${attribute}-${group}`} className="info-row">
                      <span className="text-gray-300 text-xs flex-1">
                        {group}
                      </span>
                      <span className="text-white text-xs font-mono">
                        {formatPercent(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasSHAP && hasBias && (
        <div className="feature-bias-overlay">
          <div className="feature-sidecard-title">
            <ShieldAlert className="w-4 h-4 text-yellow-400" />
            Bias Overlay
          </div>
          <div className="space-y-2">
            {biasByFeature.map((item) => (
              <div key={item.attribute} className="info-row">
                <span className="text-gray-300 text-xs flex-1">
                  {item.attribute}
                </span>
                <span className="text-yellow-300 text-xs font-medium">
                  {item.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FeatureImportance;
