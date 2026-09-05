import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as ownershipApi from '../api/ownership.js';
import OwnershipTimeline from '../components/OwnershipTimeline.jsx';
import { asList, OWNERSHIP_BADGES, OWNERSHIP_LABELS } from '../utils/constants.js';

// Ownership records across all units; selecting a record shows its full
// temporal history via GET /api/v1/ownership/history/{unit_id}.
export default function OwnershipPage() {
  const [selectedUnit, setSelectedUnit] = useState(null);

  const recordsQ = useQuery({
    queryKey: ['ownership'],
    queryFn: () => ownershipApi.listOwnership({ limit: 200 }),
  });
  const historyQ = useQuery({
    queryKey: ['ownership-history', selectedUnit],
    queryFn: () => ownershipApi.getOwnershipHistory(selectedUnit),
    enabled: Boolean(selectedUnit),
  });

  const records = asList(recordsQ.data);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="card p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Ownership Records</h2>
        {recordsQ.isLoading ? (
          <div className="text-sm text-slate-500">Loading records…</div>
        ) : recordsQ.isError ? (
          <div className="text-sm text-slate-500">
            Ownership records unavailable — is the backend running?
          </div>
        ) : records.length === 0 ? (
          <div className="text-sm text-slate-500">
            No ownership records yet — they appear after ULPIN generation.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-slate-400">
                  <th className="pb-2">Owner</th>
                  <th className="pb-2">Rights</th>
                  <th className="pb-2">Share</th>
                  <th className="pb-2">Valid from</th>
                </tr>
              </thead>
              <tbody>
                {records.map((rec, i) => {
                  const unitId = rec.unit_id;
                  return (
                    <tr
                      key={rec.ownership_id || rec.id || i}
                      className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50/50 ${
                        selectedUnit === unitId ? 'bg-brand-50' : ''
                      }`}
                      onClick={() => setSelectedUnit(unitId)}
                    >
                      <td className="py-2">{rec.owner?.name || rec.owner_name || 'Unknown'}</td>
                      <td className="py-2">
                        <span className={`badge ${OWNERSHIP_BADGES[rec.rights_type] || 'bg-slate-100 text-slate-700'}`}>
                          {OWNERSHIP_LABELS[rec.rights_type] || rec.rights_type}
                        </span>
                      </td>
                      <td className="py-2 text-xs">{rec.share_percentage != null ? `${rec.share_percentage}%` : '—'}</td>
                      <td className="py-2 text-xs">{rec.valid_from || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-2 text-xs text-slate-400">
          Click a record to view the unit's full ownership history.
        </div>
      </div>

      <div>
        {selectedUnit ? (
          historyQ.isLoading ? (
            <div className="card p-4 text-sm text-slate-500">Loading history…</div>
          ) : (
            <OwnershipTimeline records={asList(historyQ.data)} />
          )
        ) : (
          <div className="card p-4 text-sm text-slate-500">
            Select a record on the left to inspect its ownership timeline.
          </div>
        )}
      </div>
    </div>
  );
}
