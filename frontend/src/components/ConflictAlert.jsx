import { useMutation, useQueryClient } from '@tanstack/react-query';
import * as conflictsApi from '../api/conflicts.js';
import { CONFLICT_TYPES, SEVERITY_STYLES } from '../utils/constants.js';

// Single conflict alert card with severity coloring and resolve action
// (PUT /api/v1/conflicts/{id}/resolve).
export default function ConflictAlert({ conflict }) {
  const queryClient = useQueryClient();

  const resolveMutation = useMutation({
    mutationFn: () => conflictsApi.resolveConflict(conflict.alert_id || conflict.id, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conflicts'] }),
  });

  if (!conflict) return null;
  const id = conflict.alert_id || conflict.id;
  const severity = conflict.severity || 'medium';
  const status = conflict.status || 'open';
  const open = status === 'open' || status === 'under_review' || status === 'escalated';

  return (
    <div
      className={`card border-l-4 p-4 ${
        severity === 'critical'
          ? 'border-l-red-500'
          : severity === 'high'
            ? 'border-l-orange-500'
            : severity === 'medium'
              ? 'border-l-amber-400'
              : 'border-l-emerald-400'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-slate-800">
          {CONFLICT_TYPES[conflict.conflict_type] || conflict.conflict_type || 'Conflict'}
        </div>
        <div className="flex items-center gap-2">
          <span className={`badge ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium}`}>
            {severity}
          </span>
          <span className="badge bg-slate-100 text-slate-700">{status}</span>
        </div>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600">
        <div>
          Unit A: <span className="font-mono">{shortId(conflict.unit_a_id)}</span>
        </div>
        <div>
          Unit B: <span className="font-mono">{shortId(conflict.unit_b_id)}</span>
        </div>
        {conflict.overlap_volume_cubm != null && (
          <div>Overlap volume: {Number(conflict.overlap_volume_cubm).toFixed(3)} m³</div>
        )}
        {conflict.created_at && <div>Detected: {String(conflict.created_at).slice(0, 10)}</div>}
      </div>
      {open && (
        <div className="mt-3">
          <button
            type="button"
            className="btn-primary"
            disabled={resolveMutation.isPending}
            onClick={() => resolveMutation.mutate()}
          >
            {resolveMutation.isPending ? 'Resolving…' : 'Mark resolved'}
          </button>
          {resolveMutation.isError && (
            <span className="ml-2 text-xs text-red-600">Resolve failed — try again.</span>
          )}
        </div>
      )}
    </div>
  );
}

function shortId(v) {
  if (!v) return '—';
  const s = String(v);
  return s.length > 12 ? `${s.slice(0, 8)}…` : s;
}
