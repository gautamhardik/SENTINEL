import React from 'react';
import { TransactionPayload } from '../lib/types';
import { RefreshCw, Play, User, CreditCard, DollarSign, RotateCcw } from 'lucide-react';

interface TransactionFormProps {
  payload: TransactionPayload;
  setPayload: React.Dispatch<React.SetStateAction<TransactionPayload>>;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  onReset: () => void;
  hasResult: boolean;
}

export const TransactionForm: React.FC<TransactionFormProps> = ({
  payload,
  setPayload,
  onSubmit,
  isLoading,
  onReset,
  hasResult,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setPayload((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? 0 : parseFloat(value)) : value,
    }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!isLoading) {
        const form = e.currentTarget.closest('form');
        if (form) {
          form.requestSubmit();
        }
      }
    }
  };

  const handleRegenerateUUID = () => {
    const newId = `TX-${Math.random().toString(36).substring(2, 8).toUpperCase()}${Math.floor(100 + Math.random() * 900)}`;
    setPayload((prev) => ({ ...prev, transaction_id: newId }));
  };

  const handleRegenerateTimestamp = () => {
    const now = new Date().toISOString().substring(0, 19);
    setPayload((prev) => ({ ...prev, Timestamp: now }));
  };

  return (
    <form onSubmit={onSubmit} onKeyDown={handleKeyDown} className="w-full space-y-4">
      <div className="inst-card space-y-4 p-5 sm:p-6 transition-all duration-200">
        {/* SECTION 1: TRANSACTION IDENTIFIERS */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
            <CreditCard className="h-4 w-4 text-slate-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              1. Transaction Identifiers
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Transaction ID */}
            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">
                  Transaction ID <span className="text-red-500">*</span>
                </label>
                <button
                  type="button"
                  onClick={handleRegenerateUUID}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-900 disabled:opacity-50"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>Fresh ID</span>
                </button>
              </div>
              <input
                type="text"
                name="transaction_id"
                value={payload.transaction_id}
                onChange={handleChange}
                disabled={isLoading}
                required
                className="inst-input mt-1 w-full px-3 py-2 font-mono"
                placeholder="TX-99812"
              />
            </div>

            {/* Timestamp */}
            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">
                  Timestamp <span className="text-red-500">*</span>
                </label>
                <button
                  type="button"
                  onClick={handleRegenerateTimestamp}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-900 disabled:opacity-50"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>Now</span>
                </button>
              </div>
              <input
                type="text"
                name="Timestamp"
                value={payload.Timestamp}
                onChange={handleChange}
                disabled={isLoading}
                required
                className="inst-input mt-1 w-full px-3 py-2 font-mono"
                placeholder="2026-08-12T14:15:00"
              />
            </div>
          </div>
        </div>

        {/* SECTION 2: PARTIES & FINANCIAL INSTITUTIONS */}
        <div className="space-y-3 pt-1">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
            <User className="h-4 w-4 text-slate-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              2. Parties & Financial Institutions
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Originating Party (Sender) */}
            <div className="space-y-3">
              <div className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                Originating Party (Sender)
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Sender Account ID *</label>
                <input
                  type="text"
                  name="From_Account"
                  value={payload.From_Account}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                  className="inst-input mt-1 w-full px-3 py-2 font-mono"
                  placeholder="ACC_1029"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Sender Bank ID *</label>
                <input
                  type="text"
                  name="From_Bank"
                  value={payload.From_Bank}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                  className="inst-input mt-1 w-full px-3 py-2 font-mono"
                  placeholder="BANK_12"
                />
              </div>
            </div>

            {/* Destination Party (Receiver) */}
            <div className="space-y-3">
              <div className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                Destination Party (Receiver)
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Receiver Account ID *</label>
                <input
                  type="text"
                  name="To_Account"
                  value={payload.To_Account}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                  className="inst-input mt-1 w-full px-3 py-2 font-mono"
                  placeholder="ACC_8841"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Receiver Bank ID *</label>
                <input
                  type="text"
                  name="To_Bank"
                  value={payload.To_Bank}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                  className="inst-input mt-1 w-full px-3 py-2 font-mono"
                  placeholder="BANK_45"
                />
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 3: PAYMENT AMOUNTS & CURRENCY RAILS */}
        <div className="space-y-3 pt-1">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
            <DollarSign className="h-4 w-4 text-slate-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              3. Payment Amounts & Currency Rails
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {/* Amount Paid */}
            <div>
              <label className="text-xs font-semibold text-slate-700">Amount Paid (Outbound) *</label>
              <div className="relative mt-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 font-mono text-xs text-slate-400">$</span>
                <input
                  type="number"
                  step="any"
                  name="Amount_Paid"
                  value={payload.Amount_Paid || ''}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                  className="inst-input w-full pl-7 pr-3 py-2 font-mono font-semibold tabular-nums text-right"
                  placeholder="12500.00"
                />
              </div>
            </div>

            {/* Amount Received */}
            <div>
              <label className="text-xs font-semibold text-slate-700">Amount Received (Inbound) *</label>
              <div className="relative mt-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 font-mono text-xs text-slate-400">$</span>
                <input
                  type="number"
                  step="any"
                  name="Amount_Received"
                  value={payload.Amount_Received || ''}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                  className="inst-input w-full pl-7 pr-3 py-2 font-mono font-semibold tabular-nums text-right"
                  placeholder="12500.00"
                />
              </div>
            </div>

            {/* Payment Rail */}
            <div>
              <label className="text-xs font-semibold text-slate-700">Payment Rail *</label>
              <select
                name="Payment_Format"
                value={payload.Payment_Format}
                onChange={handleChange}
                disabled={isLoading}
                className="inst-input mt-1 w-full px-3 py-2"
              >
                <option value="Wire Transfer">Wire Transfer</option>
                <option value="ACH Outbound">ACH Outbound</option>
                <option value="Cheque">Cheque</option>
                <option value="Credit Card">Credit Card</option>
                <option value="Cash Deposit">Cash Deposit</option>
              </select>
            </div>

            {/* Payment Currency */}
            <div>
              <label className="text-xs font-semibold text-slate-700">Payment Currency *</label>
              <select
                name="Payment_Currency"
                value={payload.Payment_Currency}
                onChange={handleChange}
                disabled={isLoading}
                className="inst-input mt-1 w-full px-3 py-2"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="CAD">CAD ($)</option>
                <option value="AUD">AUD ($)</option>
              </select>
            </div>

            {/* Receiving Currency */}
            <div>
              <label className="text-xs font-semibold text-slate-700">Receiving Currency *</label>
              <select
                name="Receiving_Currency"
                value={payload.Receiving_Currency}
                onChange={handleChange}
                disabled={isLoading}
                className="inst-input mt-1 w-full px-3 py-2"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="CAD">CAD ($)</option>
                <option value="AUD">AUD ($)</option>
              </select>
            </div>
          </div>
        </div>

        {/* SUBMISSION & RESET ACTIONS */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-3/4 inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-6 text-xs font-bold text-white shadow-2xs transition-all hover:bg-slate-800 active:bg-slate-950 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin text-white" />
                <span>Assessing Transaction...</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Run Risk Assessment</span>
                <span className="hidden sm:inline-block text-[10px] font-mono text-slate-400 font-normal ml-1">(Ctrl+Enter)</span>
              </>
            )}
          </button>

          {hasResult ? (
            <button
              type="button"
              onClick={onReset}
              disabled={isLoading}
              className="w-1/4 inline-flex h-10 items-center justify-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-xs font-bold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span className="truncate">Assess Another Transaction</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onReset}
              disabled={isLoading}
              className="w-1/4 inline-flex h-10 items-center justify-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-600 shadow-2xs transition-colors hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset Form</span>
            </button>
          )}
        </div>
      </div>
    </form>
  );
};
