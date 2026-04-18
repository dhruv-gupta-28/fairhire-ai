import React from "react";

/**
 * ScoreGauge – a circular gauge visualising a numeric score out of 100.
 * The gauge colour changes based on the score range:
 *   >=80  → green
 *   >=60  → yellow
 *   else  → red
 */
const ScoreGauge = ({ score }) => {
  const getColor = () => {
    if (score >= 80) return "#22c55e"; // green-500
    if (score >= 60) return "#fbbf24"; // yellow-400
    return "#ef4444"; // red-500
  };

  // Stroke length for the filled arc (percentage of 100)
  const dashArray = 100;
  const dashOffset = dashArray - (score / 100) * dashArray;

  return (
    <div className="w-24 h-24 relative">
      <svg viewBox="0 0 36 36" className="w-full h-full">
        {/* Background circle */}
        <path
          className="text-gray-300 stroke-current"
          strokeWidth="3"
          fill="none"
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831"
        />
        {/* Filled portion */}
        <path
          stroke={getColor()}
          strokeWidth="3"
          fill="none"
          strokeDasharray={`${dashArray} ${dashArray}`}
          strokeDashoffset={dashOffset}
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-xl font-bold" style={{ color: getColor() }}>
        {score}
      </div>
    </div>
  );
};

export default ScoreGauge;
