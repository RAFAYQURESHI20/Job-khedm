import { useState, useEffect, useCallback } from "react";
import JobCard from "./components/JobCard";
import SearchBar from "./components/SearchBar";
import FilterPanel from "./components/FilterPanel";
import Pagination from "./components/Pagination";
import StatsHeader from "./components/StatsHeader";
import { fetchJobs, fetchStats } from "./utils/api";

const DEFAULT_FILTERS = {
  q: "",
  category: "",
  job_type: "",
  location: "",
  page: 1,
  page_size: 20,
};

export default function App() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJobs(filters);
      setJobs(data.results);
      setTotal(data.total);
    } catch (err) {
      setError("Failed to load jobs. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.warn);
  }, []);

  const handleFilterChange = (key, value) =>
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));

  const handlePageChange = (page) =>
    setFilters((prev) => ({ ...prev, page }));

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <span className="text-2xl font-bold text-indigo-600">JobPulse</span>
          <SearchBar value={filters.q} onChange={(v) => handleFilterChange("q", v)} />
        </div>
      </header>

      {stats && <StatsHeader stats={stats} />}

      <main className="max-w-6xl mx-auto px-4 py-6 flex gap-6">
        <aside className="w-56 shrink-0">
          <FilterPanel filters={filters} onChange={handleFilterChange} />
        </aside>

        <section className="flex-1">
          {error && <p className="text-red-500 mb-4">{error}</p>}
          {loading ? (
            <div className="grid gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-28 bg-gray-200 animate-pulse rounded-xl" />
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <p className="text-gray-500 text-center mt-20">No listings found.</p>
          ) : (
            <div className="grid gap-4">
              {jobs.map((job) => <JobCard key={job.id} job={job} />)}
            </div>
          )}

          <Pagination
            page={filters.page}
            pageSize={filters.page_size}
            total={total}
            onChange={handlePageChange}
          />
        </section>
      </main>
    </div>
  );
}
