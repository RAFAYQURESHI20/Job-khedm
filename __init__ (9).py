/**
 * utils/api.js
 * Thin wrapper around the JobPulse REST API.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

async function request(path, params = {}) {
  const url = new URL(`${BASE_URL}${path}`);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) url.searchParams.set(k, v);
  });

  const resp = await fetch(url.toString());
  if (!resp.ok) throw new Error(`API error ${resp.status}`);
  return resp.json();
}

export const fetchJobs = (filters) =>
  request("/jobs", {
    q: filters.q,
    category: filters.category,
    job_type: filters.job_type,
    location: filters.location,
    page: filters.page,
    page_size: filters.page_size,
  });

export const fetchJob = (id) => request(`/jobs/${id}`);
export const fetchStats = () => request("/stats/summary");
