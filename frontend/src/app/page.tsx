'use client';

import React, { useState, useRef } from 'react';
import { Header } from '../components/Header';
import { TransactionForm } from '../components/TransactionForm';
import { RiskResultHero } from '../components/RiskResultHero';
import { RiskDriversCard } from '../components/RiskDriversCard';
import { InvestigatorCard } from '../components/InvestigatorCard';
import { TransactionPayload, PredictionResponse } from '../lib/types';
import { predictTransaction } from '../lib/api';
import { AlertCircle, RefreshCw } from 'lucide-react';

const createDefaultPayload = (): TransactionPayload => ({
  transaction_id: `TX-${Math.random().toString(36).substring(2, 8).toUpperCase()}${Math.floor(100 + Math.random() * 900)}`,
  Timestamp: new Date().toISOString().substring(0, 19),
  From_Account: 'ACC_1029',
  To_Account: 'ACC_8841',
  From_Bank: 'BANK_12',
  To_Bank: 'BANK_45',
  Amount_Paid: 12500.0,
  Amount_Received: 12500.0,
  Payment_Format: 'Wire Transfer',
  Payment_Currency: 'USD',
  Receiving_Currency: 'USD',
});

export default function Home() {
  const [payload, setPayload] = useState<TransactionPayload>(createDefaultPayload);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const res = await predictTransaction(payload);
      setResponse(res);
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err: any) {
      setError(err?.message || 'An unexpected error occurred during transaction assessment.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setPayload(createDefaultPayload());
    setResponse(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 font-sans">
      <Header />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-5 sm:px-6 sm:py-6">
        <div className="space-y-5">
          {/* Form Page Title & Subtitle */}
          <div className="space-y-1">
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900">
              Single-Transaction Risk Assessment
            </h1>
            <p className="text-xs font-medium text-slate-500">
              Screen one transaction and receive a calibrated risk assessment with explainable decision drivers.
            </p>
          </div>

          {/* Screening Form */}
          <TransactionForm
            payload={payload}
            setPayload={setPayload}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            onReset={handleReset}
            hasResult={!!response}
          />

          {/* Error Banner */}
          {error && (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-900" role="alert">
              <AlertCircle className="h-4.5 w-4.5 shrink-0 text-red-600 stroke-[2]" />
              <div className="flex-1 space-y-1">
                <h4 className="font-bold text-red-900">Assessment Error</h4>
                <p className="text-red-800 font-medium">{error}</p>
                {(error.includes('503') || error.includes('500') || error.toLowerCase().includes('failed to fetch') || error.toLowerCase().includes('network')) && (
                  <p className="text-[11px] text-red-700 font-mono bg-red-100/60 p-2 rounded border border-red-200 mt-2">
                    💡 Troubleshooting: Ensure backend API is active on port 8000. If running locally outside Docker, start PostgreSQL or launch backend with <span className="font-bold">DB_ENGINE_TYPE=duckdb</span>.
                  </p>
                )}
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={handleSubmit}
                    className="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-3 py-1 font-semibold text-red-800 shadow-2xs hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:outline-none"
                  >
                    <RefreshCw className="h-3 w-3" />
                    <span>Retry Assessment</span>
                  </button>
                </div>
              </div>
            </div>
          )}


          {/* Results Viewport Anchor with Sticky Header Offset */}
          {response && (
            <div ref={resultRef} className="space-y-4 pt-2 scroll-mt-20 animate-in fade-in duration-200">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                  Risk Assessment Results
                </h2>
                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex items-center gap-1 text-xs font-bold text-slate-600 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:outline-none rounded px-1"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Assess Another Transaction</span>
                </button>
              </div>

              {/* P0 Result Hero */}
              <RiskResultHero response={response} />

              {/* P1 Top Risk Drivers */}
              <RiskDriversCard drivers={response.explanation?.top_risk_drivers || []} rawPaymentFormat={payload.Payment_Format} timestamp={response.timestamp} />

              {/* P2 Structured Investigator Report */}
              <InvestigatorCard response={response} rawPaymentFormat={payload.Payment_Format} />
            </div>
          )}
        </div>
      </main>

      <footer className="mt-8 border-t border-slate-200 bg-white py-3 text-center text-[11px] font-medium text-slate-400">
        Sentinel Risk Engine · Single-Transaction Financial Risk Instrument
      </footer>
    </div>
  );
}
