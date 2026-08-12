import { TransactionPayload, PredictionResponse, ApiErrorPayload } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function predictTransaction(payload: TransactionPayload): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorData: ApiErrorPayload;
    try {
      errorData = await response.json();
    } catch {
      throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
    }
    
    if (errorData?.error?.message) {
      throw new Error(errorData.error.message);
    }
    throw new Error(`API Request failed with status ${response.status}`);
  }

  return response.json();
}
