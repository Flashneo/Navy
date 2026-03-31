const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface Job {
  linkedin_id: string;
  title: string;
  company_name: string;
  company_linkedin_url: string | null;
  location: string;
  job_url: string;
  description?: string;
  seniority_level: string | null;
  employment_type: string | null;
  posted_date: string | null;
  relevance_score: number;
  score_reasoning: string | null;
  matched_keywords: string[];
  first_seen_at: string;
  last_seen_at: string;
}

export interface JobsResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface Run {
  id: number;
  started_at: string;
  completed_at: string | null;
  jobs_found: number;
  jobs_new: number;
  jobs_passed_filter: number;
  status: string;
}

export interface Stats {
  total_jobs: number;
  new_this_week: number;
  avg_score: number;
  total_runs: number;
  last_run: Run | null;
  top_companies: { name: string; count: number }[];
}

export interface ActiveRun {
  active: boolean;
  status?: string;
  dry_run?: boolean;
  skip_enrichment?: boolean;
  progress?: {
    step: string;
    jobs_found: number;
    jobs_new: number;
    jobs_passed: number;
  };
}

export const api = {
  getStats: () => fetchAPI<Stats>("/api/stats"),

  getJobs: (params?: {
    q?: string;
    min_score?: number;
    page?: number;
    per_page?: number;
    sort_by?: string;
    sort_order?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set("q", params.q);
    if (params?.min_score) searchParams.set("min_score", String(params.min_score));
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.per_page) searchParams.set("per_page", String(params.per_page));
    if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
    if (params?.sort_order) searchParams.set("sort_order", params.sort_order);
    return fetchAPI<JobsResponse>(`/api/jobs?${searchParams}`);
  },

  getJob: (id: string) => fetchAPI<Job & { company: any }>(`/api/jobs/${id}`),

  getRuns: (page = 1) =>
    fetchAPI<{ runs: Run[]; total: number; page: number; per_page: number }>(
      `/api/runs?page=${page}`
    ),

  getActiveRun: () => fetchAPI<ActiveRun>("/api/runs/active"),

  triggerRun: (options: { dry_run?: boolean; skip_enrichment?: boolean }) =>
    fetchAPI<{ message: string; active_run: any }>("/api/runs", {
      method: "POST",
      body: JSON.stringify(options),
    }),

  stopRun: () =>
    fetchAPI<{ message: string }>("/api/runs/stop", { method: "POST" }),

  getConfig: () => fetchAPI<any>("/api/config"),

  updateConfig: (config: any) =>
    fetchAPI<{ message: string; config: any }>("/api/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),

  getExportUrl: (format: "csv" | "json") =>
    `${API_BASE}/api/export?format=${format}`,
};
