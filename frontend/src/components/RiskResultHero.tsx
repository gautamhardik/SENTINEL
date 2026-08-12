import React, { useState } from 'react';
import { PredictionResponse } from '../lib/types';
import { mapBackendResponseToPresentation } from '../lib/mapper';
import { AlertTriangle, CheckCircle2, ShieldAlert, AlertOctagon, Zap, Copy, Check } from 'lucide-react';

interface RiskResultHeroProps {
  response: PredictionResponse;
}

export const RiskResultHero: React.FC<RiskResultHeroProps> = ({ response }) => {
  const [copiedTxId, setCopiedTxId] = useState(false);
  const presentation = mapBackendResponseToPresentation(response);
  const prob = response.calibrated_probability ?? response.fraud_probability ?? 0;
  const thresh = response.threshold ?? 0.255656;

  const probPercent = Math.min(100, Math.max(0, prob * 100));
  const threshPercent = Math.min(100, Math.max(0, thresh * 100));

  const deltaPct = (prob - thresh) * 100;
  const isAboveThresh = deltaPct > 0;
  const deltaText = `${Math.abs(deltaPct).toFixed(2)} percentage points ${isAboveThresh ? 'above' : 'below'} optimal threshold`;

  const rawLatencyMs = response.inference_latency_ms || 0;
  const latencyText = rawLatencyMs >= 1000
    ? `Initial processing · ${(rawLatencyMs / 1000).toFixed(2)}s`
    : `Inference · ${rawLatencyMs.toFixed(1)} ms`;

  const handleCopyTxId = async () => {
    try {
      await navigator.clipboard.writeText(response.transaction_id);
      setCopiedTxId(true);
      setTimeout(() => setCopiedTxId(false), 2000);
    } catch {
      // Fallback
    }
  };

  const renderIcon = () => {
    switch (response.decision) {
      case 'APPROVED_LEGITIMATE':
        return <CheckCircle2 className="h-4 w-4 text-emerald-700" />;
      case 'APPROVED_WITH_MONITORING':
        return <AlertTriangle className="h-4 w-4 text-amber-700" />;
      case 'FLAGGED_FRAUD':
        return <ShieldAlert className="h-4 w-4 text-red-700" />;
      case 'FLAGGED_CRITICAL_FRAUD':
        return <AlertOctagon className="h-4 w-4 text-rose-800" />;
      default:
        return <CheckCircle2 className="h-4 w-4 text-slate-700" />;
    }
  };

  const getMeterColor = () => {
    if (prob >= 0.75) return 'bg-rose-700';
    if (isAboveThresh) return 'bg-red-600';
    if (prob >= 0.10) return 'bg-amber-500';
    return 'bg-emerald-600';
  };

  return (
    <section className="inst-card w-full space-y-4 p-5 sm:p-6 transition-all duration-200" aria-live="polite">
      {/* Context Metadata Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5 text-xs">
        <div className="flex items-center gap-2 font-mono text-slate-600">
          <button
            type="button"
            onClick={handleCopyTxId}
            title="Click to copy Transaction ID"
            className="inline-flex items-center gap-1.5 rounded border border-slate-200 bg-slate-100 px-2 py-0.5 font-bold text-slate-900 transition-colors hover:bg-slate-200 active:bg-slate-300"
          >
            {copiedTxId ? (
              <>
                <Check className="h-3 w-3 text-emerald-600 stroke-[2.5]" />
                <span className="text-emerald-700">Copied {response.transaction_id}</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3 text-slate-400" />
                <span>{response.transaction_id}</span>
              </>
            )}
          </button>
          <span className="text-slate-300">•</span>
          <span>{response.timestamp}</span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px] text-slate-500">
          <Zap className="h-3.5 w-3.5 text-amber-500" />
          <span><strong className="font-bold text-slate-900">{latencyText}</strong></span>
        </div>
      </div>

      {/* P0 Hero Section */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Left Column: Decision & Calibrated Probability */}
        <div className="flex flex-col justify-between space-y-3 rounded-lg border border-slate-200 bg-slate-50/50 p-4 sm:p-5">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                Fraud Risk Assessment
              </span>
              <div
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5 text-xs font-bold tracking-wide ${presentation.badgeBgClass} ${presentation.badgeColorClass} ${presentation.badgeBorderClass}`}
              >
                {renderIcon()}
                <span>{presentation.badgeLabel}</span>
              </div>
            </div>

            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-mono text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 tabular-nums">
                {presentation.probabilityFormatted}
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Calibrated Score
              </span>
            </div>

            {/* Risk Scale Boundary Indicator aligned with 10% / 25.57% / 75% backend policy */}
            <div className="mt-4 space-y-1.5">
              <div className="flex items-center justify-between text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500">
                <span>0% Low (&lt;10%)</span>
                <span className="text-slate-800">Boundary ({presentation.thresholdFormatted})</span>
                <span>75% Critical</span>
              </div>

              <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-200 p-0.5">
                {/* 10% monitoring marker pin */}
                <div
                  className="absolute bottom-0 top-0 z-10 w-0.5 bg-amber-400"
                  style={{ left: '10%' }}
                  title="10.0% Monitoring Boundary"
                />
                {/* 25.57% optimal decision boundary pin */}
                <div
                  className="absolute bottom-0 top-0 z-10 w-0.5 bg-slate-900"
                  style={{ left: `${threshPercent}%` }}
                  title="25.57% Optimal Decision Boundary"
                />
                {/* 75% critical fraud boundary pin */}
                <div
                  className="absolute bottom-0 top-0 z-10 w-0.5 bg-rose-700"
                  style={{ left: '75%' }}
                  title="75.0% Critical Fraud Boundary"
                />
                <div
                  className={`h-full rounded-full transition-all duration-500 ${getMeterColor()}`}
                  style={{ width: `${probPercent}%` }}
                />
              </div>

              <div className="pt-0.5 text-right font-mono text-[11px] font-semibold text-slate-700">
                <span>{deltaText}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Recommended Action */}
        <div
          className={`flex flex-col justify-between rounded-lg border p-4 sm:p-5 ${presentation.actionBgClass} ${presentation.actionBorderClass}`}
        >
          <div>
            <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
              Recommended Action
            </span>
            <h3 className={`mt-1.5 text-xl sm:text-2xl font-black tracking-tight ${presentation.actionTextClass}`}>
              {presentation.actionTitle}
            </h3>
            <p className="mt-2 text-xs font-medium leading-relaxed text-slate-600">
              {presentation.actionDescription}
            </p>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-slate-200/80 pt-2.5 text-[11px] font-semibold text-slate-500">
            <span>Action Code: <strong className="font-mono text-slate-900">{response.recommended_action || presentation.systemActionCode}</strong></span>
            <span>Risk Level: <strong className="font-mono uppercase text-slate-900">{response.risk_level}</strong></span>
          </div>
        </div>
      </div>
    </section>
  );
};
