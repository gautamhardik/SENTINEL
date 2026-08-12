import React, { useState } from 'react';
import { PredictionResponse } from '../lib/types';
import { mapBackendResponseToPresentation, formatFeatureName, formatFeatureObservedValue, generateAssessmentClipboardText } from '../lib/mapper';
import { Copy, Check, FileCheck, ChevronDown, ChevronUp, Cpu } from 'lucide-react';

interface InvestigatorCardProps {
  response: PredictionResponse;
  rawPaymentFormat?: string;
}

export const InvestigatorCard: React.FC<InvestigatorCardProps> = ({ response, rawPaymentFormat }) => {
  const [copied, setCopied] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!response) {
    return null;
  }

  const presentation = mapBackendResponseToPresentation(response);
  const topDrivers = response.explanation?.top_risk_drivers || [];

  const prob = response.calibrated_probability ?? response.fraud_probability ?? 0;
  const thresh = response.threshold ?? 0.2557;
  const deltaPct = (prob - thresh) * 100;
  const isAboveThresh = deltaPct > 0;
  const deltaText = `${Math.abs(deltaPct).toFixed(2)} percentage points ${isAboveThresh ? 'above' : 'below'} threshold`;

  const handleCopy = async () => {
    try {
      const cleanText = generateAssessmentClipboardText(response, rawPaymentFormat);
      await navigator.clipboard.writeText(cleanText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <section className="inst-card w-full space-y-5 p-5 sm:p-6 transition-all duration-200">
      {/* SECTION 1 — HEADER */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
            <FileCheck className="h-4.5 w-4.5 stroke-[2]" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Investigator Risk Assessment Report
            </h3>
            <p className="text-[11px] font-medium text-slate-500">
              Structured decision log for compliance & manual audit trail
            </p>
          </div>
        </div>
        <button
          onClick={handleCopy}
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 active:bg-slate-100"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-600 stroke-[2.5]" />
              <span className="text-emerald-700">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 text-slate-500" />
              <span>Copy assessment</span>
            </>
          )}
        </button>
      </div>

      {/* SECTION 3 — STRUCTURED ASSESSMENT SUMMARY */}
      <div className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-4 rounded-lg border border-slate-200 bg-slate-50/70 p-4">
          <div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              System Decision
            </span>
            <div className="mt-1">
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-extrabold tracking-wide ${presentation.badgeBgClass} ${presentation.badgeColorClass} ${presentation.badgeBorderClass}`}>
                {presentation.decisionText}
              </span>
            </div>
          </div>

          <div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Fraud Probability
            </span>
            <div className="mt-1 font-mono text-base font-extrabold text-slate-900">
              {presentation.probabilityFormatted}
            </div>
          </div>

          <div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Decision Boundary
            </span>
            <div className="mt-1 font-mono text-base font-bold text-slate-700">
              {presentation.thresholdFormatted}
            </div>
          </div>

          <div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Recommended Action
            </span>
            <div className="mt-1 font-mono text-xs font-bold text-slate-900 uppercase">
              {response.recommended_action || presentation.systemActionCode}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs font-medium text-slate-500 px-1">
          <span>Boundary Evaluation: <strong className="font-mono text-slate-800">{deltaText}</strong></span>
          <span>Model Version: <strong className="font-mono text-slate-800">{response.model_version || 'v1.0.0'}</strong></span>
        </div>
      </div>

      {/* SECTION 7 — KEY RISK INDICATORS */}
      <div className="space-y-3 border-t border-slate-200 pt-4">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
            Key Risk Indicators
          </h4>
          <span className="text-[11px] font-medium text-slate-400">Model Attribution Factors</span>
        </div>

        <div className="space-y-2">
          {topDrivers.slice(0, 4).map((driver, index) => {
            const rawImpact = driver.impact ?? driver.shap_impact ?? 0;
            const isIncrease = rawImpact > 0;
            const isNeutral = rawImpact === 0;
            const impactFormatted = isIncrease ? `+${rawImpact.toFixed(2)}` : rawImpact.toFixed(2);
            const humanName = formatFeatureName(driver.feature);
            const observedValue = formatFeatureObservedValue(driver.feature, driver.value, rawPaymentFormat, response.timestamp);

            return (
              <div
                key={index}
                className="flex items-center justify-between rounded-md border border-slate-200 bg-white p-3 text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <span className={`h-2 w-2 rounded-full ${isIncrease ? 'bg-red-500' : (isNeutral ? 'bg-slate-400' : 'bg-emerald-500')}`} />
                  <div>
                    <span className="font-bold text-slate-900">{humanName}</span>
                    <span className="ml-2 font-mono text-[11px] text-slate-500">• {observedValue}</span>
                  </div>
                </div>

                <div className="font-mono text-xs font-semibold text-slate-700">
                  <span className={isIncrease ? 'text-red-700 font-bold' : (isNeutral ? 'text-slate-700' : 'text-emerald-700 font-bold')}>
                    {isIncrease ? '↑ Higher Risk Contribution' : (isNeutral ? '→ Neutral Contribution' : '↓ Lower Risk Contribution')} · {impactFormatted}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

