import React from "react";
import { CheckCircle2, ChevronRight, Lock } from "lucide-react";

const GuidedStepper = ({ steps, currentStep, highestStep, onStepChange }) => {
  return (
    <div className="guided-stepper card mb-5">
      <div className="guided-stepper-header">
        <div>
          <h2 className="section-heading text-sm mb-1">Guided Flow</h2>
          <p className="text-gray-500 text-xs">
            Complete each step in order to keep the analysis state clean.
          </p>
        </div>
        <div className="guided-stepper-badge">
          Step {currentStep} of {steps.length}
        </div>
      </div>

      <div className="guided-stepper-track">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isComplete = highestStep > stepNumber;
          const isCurrent = currentStep === stepNumber;
          const isLocked = stepNumber > highestStep;

          return (
            <React.Fragment key={step.id}>
              <button
                type="button"
                className={`guided-step ${
                  isCurrent
                    ? "guided-step-current"
                    : isComplete
                      ? "guided-step-complete"
                      : isLocked
                        ? "guided-step-locked"
                        : "guided-step-open"
                }`}
                onClick={() => {
                  if (!isLocked) {
                    onStepChange(stepNumber);
                  }
                }}
                disabled={isLocked}
              >
                <span className="guided-step-icon">
                  {isComplete ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : isLocked ? (
                    <Lock className="w-3.5 h-3.5" />
                  ) : (
                    <span>{stepNumber}</span>
                  )}
                </span>
                <span className="guided-step-text">
                  <span className="guided-step-label">{step.label}</span>
                  <span className="guided-step-hint">{step.hint}</span>
                </span>
              </button>

              {index < steps.length - 1 && (
                <div
                  className={`guided-step-connector ${
                    highestStep > stepNumber
                      ? "guided-step-connector-active"
                      : ""
                  }`}
                >
                  <ChevronRight className="w-4 h-4" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default GuidedStepper;
