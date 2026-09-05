import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as conflictsApi from '../api/conflicts.js';
import ConflictAlert from '../components/ConflictAlert.jsx';
import { asList } from '../utils/constants.js';

// Conflict alert list with severity filter and per-alert resolution
// (PUT /api/v1/conflicts/{id}/resolve).
export default function ConflictPage() {
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('open');

  const conflictsQ = useQuery({
    queryKey: ['conflicts', { severity: severityFilter, status: statusFilter }],
    queryFn: () =>
      conflictsApi.listConflicts({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit: 200,
      }),
    retry: false,
  });

  const conflicts = useMemo(
    () => asList(conflictsQ.data),
    [conflictsQ.data],
  );

  const counts = useMemo(() => {
    const c = { open: 0, high: 0, critical: 0 };
    conflicts.forEach((conflict) => {
      if (conflict.status === 'open') c.open += 1;
      if (conflict.severity === 'high') c.high += 1;
      if (conflict.severity === 'critical') c.critical += 1;
    });
    return c;
  }, [conflicts]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4">
          <div className="text-xs uppercase text-slate-400">Open</div>
          <div className="text-2xl font-bold text-slate-800">{counts.open}</div>
        </div>
        <div className="card p-4">
          <div className="text-xs uppercase text-slate-400">High severity</div>
          <div className="text-2xl font-bold text-orange-600">{counts.high}</div>
        </div>
        <div className="card p-4">
          <div className="text-xs uppercase text-slate-400">Critical</div>
          <div className="text-2xl font-bold text-red-600">{counts.critical}</div>
        </div>
      </div>

      <div className="card p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800">Conflict Alerts</h2>
          <div className="ml-auto flex items-center gap-2">
            <select
              className="input w-auto"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="">All severities</option>
              {['low', 'medium', 'high', 'critical'].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select
              className="input w-auto"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All statuses</option>
              {['open', 'under_review', 'escalated', 'resolved'].map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>

        {conflictsQ.isLoading ? (
          <div className="text-sm text-slate-500">Loading conflicts…</div>
        ) : conflictsQ.isError ? (
          <div className="text-sm text-slate-500">
            No conflict data available — run conflict detection from the backend or check that the
            API is running.
          </div>
        ) : conflicts.length === 0 ? (
          <div className="text-sm text-slate-500">
            No conflicts match these filters. 3D topology validation will flag overlaps, gaps and
            air-right violations here.
          </div>
        ) : (
          <div className="space-y-3">
            {conflicts.map((c) => (
              <ConflictAlert key={c.alert_id || c.id} conflict={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
