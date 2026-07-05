import type {
  DashboardResponse,
  DataRefreshResponse,
  PolicyResponse,
  StrategyDetail
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const headers =
    options?.method && options.method !== "GET"
      ? {
          "Content-Type": "application/json",
          ...(options?.headers || {})
        }
      : options?.headers;
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers
    });
  } catch (error) {
    throw new Error("Unable to reach the trading API.");
  }

  if (!response.ok) {
    let message = "Trading API request failed.";
    try {
      const payload = await response.json();
      message = payload.detail || payload.error || message;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}

function dashboardParams(initialCapital: number, useRealData: boolean) {
  const params = new URLSearchParams({
    initial_capital: String(initialCapital),
    use_real_data: String(useRealData)
  });
  return params.toString();
}

export function fetchPolicy(): Promise<PolicyResponse> {
  return fetchJson<PolicyResponse>("/api/policy");
}

export function fetchDashboard(
  initialCapital: number,
  useRealData: boolean
): Promise<DashboardResponse> {
  return fetchJson<DashboardResponse>(
    `/api/dashboard?${dashboardParams(initialCapital, useRealData)}`
  );
}

export function fetchStrategyDetail(
  strategyId: string,
  initialCapital: number,
  useRealData: boolean
): Promise<StrategyDetail> {
  return fetchJson<StrategyDetail>(
    `/api/strategies/${strategyId}?${dashboardParams(initialCapital, useRealData)}`
  );
}

export function refreshYahooData(initialCapital: number): Promise<DataRefreshResponse> {
  const params = new URLSearchParams({
    initial_capital: String(initialCapital)
  });
  return fetchJson<DataRefreshResponse>(`/api/data/refresh-yahoo?${params.toString()}`, {
    method: "POST"
  });
}
