import React, { useState } from 'react';
import { RiskDriver } from '../lib/types';
import { formatFeatureName, formatFeatureObservedValue } from '../lib/mapper';
import { ArrowUpRight, ArrowDownRight, ChevronDown, ChevronUp, Cpu } from 'lucide-react';

interface RiskDriversCardProps {
  drivers: RiskDriver[];
  rawPaymentFormat?: string;
  timestamp?: string;
}

export const RiskDriversCard: React.FC<RiskDriversCardProps> = ({ drivers, rawPaymentFormat, timestamp }) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!drivers || drivers.length === 0) {
    return (
      <section className="inst-card w-full p-5 sm:p-6 text-center text-xs text-slate-500 font-medium">
        No dominant model risk factors identified.
      </section>
    );
  }

  const topDrivers = drivers.slice(0, 5);

  return (
    <section className="inst-card w-full space-y-4 p-5 sm:p-6 transition-all duration-200">
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900">
            Key Risk Drivers
          </h3>
          <p className="text-xs font-medium text-slate-500">
            Primary transaction factors contributing to the calibrated risk score
          </p>
        </div>
        <span className="rounded border border-slate-200 bg-slate-100 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-slate-700">
          Primary Risk Factors
        </span>
      </div>

      <div className="space-y-2.5">
        {topDrivers.map((driver, index) => {
          const rawImpact = driver.impact ?? driver.shap_impact ?? 0;
          const isIncrease = rawImpact > 0;
          const isNeutral = rawImpact === 0;
          const impactFormatted = isIncrease ? `+${rawImpact.toFixed(2)}` : rawImpact.toFixed(2);
          const humanName = formatFeatureName(driver.feature);
          const observedValue = formatFeatureObservedValue(driver.feature, driver.value, rawPaymentFormat, timestamp);

          return (
            <div
              key={index}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3.5 text-xs transition-colors hover:bg-slate-50"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`flex h-7 w-7 items-center justify-center rounded-md border ${
                    isIncrease ? 'border-red-200 bg-red-50 text-red-700' : (isNeutral ? 'border-slate-200 bg-slate-50 text-slate-600' : 'border-emerald-200 bg-emerald-50 text-emerald-700')
                  }`}
                >
                  {isIncrease ? (
                    <ArrowUpRight className="h-4 w-4 stroke-[2.5]" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4 stroke-[2.5]" />
                  )}
                </div>
                <div>
                  <div className="font-bold text-slate-900">
                    {humanName}
                  </div>
                  <div className="text-[11px] font-medium text-slate-500 font-mono">
                    {observedValue}
                  </div>
                </div>
              </div>

              <div className="text-right font-mono">
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${
                    isIncrease ? 'border-red-200 bg-red-50 text-red-700' : (isNeutral ? 'border-slate-200 bg-slate-50 text-slate-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700')
                  }`}
                >
                  <span>{isIncrease ? '↑ Higher Risk Contribution' : (isNeutral ? '→ Neutral Contribution' : '↓ Lower Risk Contribution')}</span>
                  <span>({impactFormatted})</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Progressive Disclosure: Technical Model Detail */}
      <div className="border-t border-slate-200 pt-3">
        <button
          type="button"
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors focus:outline-none"
          aria-expanded={showTechnicalDetails}
        >
          <Cpu className="h-3.5 w-3.5 text-slate-400" />
          <span>{showTechnicalDetails ? 'Hide model detail' : 'View model detail'}</span>
          {showTechnicalDetails ? (
            <ChevronUp className="h-3.5 w-3.5 text-slate-400" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          )}
        </button>

        {showTechnicalDetails && (
          <div className="mt-3 space-y-2 rounded-lg border border-slate-200 bg-slate-900 p-4 text-slate-100 font-mono text-xs animate-in fade-in duration-150">
            <div className="text-[11px] text-slate-400 pb-1 italic border-b border-slate-800/80">
              Internal model representation — shown for technical auditability.
            </div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 text-[11px] text-slate-400 font-semibold uppercase tracking-wider pt-1">
              <span>Feature Key</span>
              <span>Model Value</span>
              <span>Exact SHAP Contribution</span>
            </div>
            {topDrivers.map((driver, index) => {
              const rawImpact = driver.impact ?? driver.shap_impact ?? 0;
              const impactFormatted = rawImpact > 0 ? `+${rawImpact.toFixed(4)}` : rawImpact.toFixed(4);

              return (
                <div key={index} className="flex items-center justify-between py-1 border-b border-slate-800/60 last:border-0 text-[11px]">
                  <span className="text-slate-300 font-mono">{driver.feature}</span>
                  <span className="text-slate-400 font-mono">{String(driver.value)}</span>
                  <span className={rawImpact > 0 ? 'text-red-400 font-bold' : (rawImpact < 0 ? 'text-emerald-400 font-bold' : 'text-slate-400')}>
                    {impactFormatted}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};
