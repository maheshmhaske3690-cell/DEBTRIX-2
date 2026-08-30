const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PriorityFix {
  file_path: string;
  rank: number;
  estimated_monthly_loss: number;
  reason_summary: string;
}

export interface DashboardData {
  scan_job_id: string;
  commit_sha: string | null;
  scanned_at: string;
  overall_health_score: number | null;
  monthly_financial_loss: number | null;
  currency: string;
  estimated_dev_hours_wasted_monthly: number | null;
  time_to_market_delay_days: number | null;
  top_3_priority_fixes: PriorityFix[];
}

export interface RepoSummary {
  id: string;
  full_name: string;
  default_branch: string;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("debtrix_token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  getConnectedRepos: () => apiFetch<RepoSummary[]>("/api/repositories/"),
  triggerScan: (repositoryId: string) =>
    apiFetch<{ scan_job_id: string; status: string }>(`/api/repositories/${repositoryId}/scan`, {
      method: "POST",
    }),
  getScanStatus: (scanJobId: string) =>
    apiFetch<{ status: string; error_message: string | null }>(`/api/dashboard/scan/${scanJobId}/status`),
  getLatestDashboard: (repositoryId: string) =>
    apiFetch<DashboardData>(`/api/dashboard/repository/${repositoryId}/latest`),
  githubLoginUrl: () => `${API_BASE_URL}/api/auth/github/login`,
};
