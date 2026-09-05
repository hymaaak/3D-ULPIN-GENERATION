import { OWNERSHIP_BADGES, OWNERSHIP_LABELS } from '../utils/constants.js';

// Vertical timeline of ownership records for one unit (newest first).
export default function OwnershipTimeline({ records = [] }) {
  if (!records.length) {
    return (
      <div className="card p-4 text-sm text-slate-500">
        No ownership history found for this unit.
      </div>
    );
  }

  const sorted = [...records].sort((a, b) =>
    String(b.valid_from || '').localeCompare(String(a.valid_from || '')),
  );

  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-800">Ownership Timeline</h3>
      <ol className="relative ml-2 space-y-4 border-l border-slate-200 pl-5">
        {sorted.map((rec, i) => {
          const active = !rec.valid_to;
          const rights = rec.rights_type || 'full_ownership';
          return (
            <li key={rec.ownership_id || rec.id || i} className="relative">
              <span
                className={`absolute -left-[26px] top-1 h-3 w-3 rounded-full border-2 ${
                  active ? 'border-emerald-500 bg-emerald-100' : 'border-slate-300 bg-white'
                }`}
              />
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-slate-800">
                  {rec.owner?.name || rec.owner_name || 'Unknown owner'}
                </span>
                <span className={`badge ${OWNERSHIP_BADGES[rights] || 'bg-slate-100 text-slate-700'}`}>
                  {OWNERSHIP_LABELS[rights] || rights}
                </span>
                {active && <span className="badge bg-emerald-100 text-emerald-800">Current</span>}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {rec.valid_from || '—'} → {rec.valid_to || 'present'}
                {rec.share_percentage != null && ` · ${Number(rec.share_percentage)}% share`}
              </div>
              {rec.registration_doc_url && (
                <a
                  href={rec.registration_doc_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-medium text-brand-600 hover:underline"
                >
                  View registration document
                </a>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
