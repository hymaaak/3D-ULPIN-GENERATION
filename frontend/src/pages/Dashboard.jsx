import { Link } from 'react-router-dom';
import { useParcels, useBuildings, useUnits } from '../hooks/useParcels.js';
import { useJobs } from '../hooks/useJobs.js';
import { useQuery } from '@tanstack/react-query';
import * as conflictsApi from '../api/conflicts.js';
import {
  asList,
  JOB_STATUS_STYLES,
  JOB_TYPE_LABELS,
} from '../utils/constants.js';

function StatCard({ title, value, to, hint }) {
  return (
    <Link to={to} className="card block p-4 transition-shadow hover:shadow-md">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-1 text-2xl font-bold text-slate-800">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </Link>
  );
}

function count(data, list) {
  return data?.total ?? data?.count ?? list.length ?? '—';
}

export default function Dashboard() {
  const parcelsQ = useParcels();
  const buildingsQ = useBuildings();
  const unitsQ = useUnits();
  const conflictsQ = useQuery({
    queryKey: ['conflicts', 'open'],
    queryFn: () => conflictsApi.listConflicts({ status: 'open' }),
    retry: false,
  });
  const jobsQ = useJobs();

  const conflicts = asList(conflictsQ.data);
  const openConflicts = conflicts.filter(
    (c) => c.status === 'open' || c.status === 'escalated',
  ).length;
  const recentJobs = asList(jobsQ.data).slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard title="Parcels" value={count(parcelsQ.data, parcelsQ.parcels)} to="/map" hint="Registered parcels" />
        <StatCard title="Buildings" value={count(buildingsQ.data, buildingsQ.buildings)} to="/map" hint="ML-extracted" />
        <StatCard title="Units" value={count(unitsQ.data, unitsQ.units)} to="/ulpin" hint="3D volumes" />
        <StatCard
          title="Open Conflicts"
          value={conflictsQ.isError ? '—' : openConflicts}
          to="/conflicts"
          hint={conflictsQ.isError ? 'Backend unavailable' : 'Needs review'}
        />
      </div>

      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Recent Activity</h2>
          <Link to="/upload" className="text-xs font-medium text-brand-600 hover:underline">
            Upload data →
          </Link>
        </div>
        {jobsQ.isError ? (
          <div className="text-sm text-slate-500">
            No processing jobs found — the backend may still be starting up.
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="text-sm text-slate-500">
            No jobs yet. Upload drone imagery or LiDAR to generate 3D ULPINs.
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-slate-400">
                <th className="pb-2">Job</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {recentJobs.map((job) => (
                <tr key={job.job_id || job.id} className="border-t border-slate-100">
                  <td className="py-2 font-mono text-xs">{shortId(job.job_id || job.id)}</td>
                  <td className="py-2">{JOB_TYPE_LABELS[job.job_type] || job.job_type || '—'}</td>
                  <td className="py-2">
                    <span className={`badge ${JOB_STATUS_STYLES[job.status] || 'bg-slate-100 text-slate-700'}`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="py-2 text-xs text-slate-500">
                    {job.confidence_score != null ? `${(job.confidence_score * 100).toFixed(1)}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function shortId(v) {
  if (!v) return '—';
  const s = String(v);
  return s.length > 12 ? `${s.slice(0, 8)}…` : s;
}
