import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useUnits, useUnitByUlpin } from '../hooks/useParcels.js';
import ParcelSearch from '../components/ParcelSearch.jsx';
import ULPINCard from '../components/ULPINCard.jsx';
import {
  OWNERSHIP_BADGES,
  OWNERSHIP_LABELS,
  PARCEL_STATUS_STYLES,
} from '../utils/constants.js';

// Registry of all generated 3D ULPINs with pattern search and CSV export.
export default function ULPINManager() {
  const [searchParams] = useSearchParams();
  const [lookupUlpin, setLookupUlpin] = useState(searchParams.get('q') || '');
  const [typeFilter, setTypeFilter] = useState('');

  const { units, isLoading, isError } = useUnits({ limit: 500 });
  const lookupQ = useUnitByUlpin(lookupUlpin);

  const filtered = useMemo(() => {
    const list = typeFilter ? units.filter((u) => u.unit_type === typeFilter) : units;
    return [...list].sort((a, b) => String(a.unit_ulpin).localeCompare(String(b.unit_ulpin)));
  }, [units, typeFilter]);

  const exportCsv = () => {
    const rows = [
      ['ulpin', 'unit_type', 'floor', 'area_sqm', 'volume_cubm', 'status'],
      ...filtered.map((u) => [
        u.unit_ulpin || '',
        u.unit_type || '',
        u.floor_number ?? '',
        u.area_sqm ?? '',
        u.volume_cubm ?? '',
        u.status || '',
      ]),
    ];
    const csv = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ulpin-registry.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const unitTypes = useMemo(
    () => [...new Set(units.map((u) => u.unit_type).filter(Boolean))],
    [units],
  );

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-800">ULPIN Lookup</h2>
        <ParcelSearch
          placeholder="Type a ULPIN or pattern, e.g. 3D-ULPIN-27-023…"
          onSelect={(item) => setLookupUlpin(item.unit_ulpin || item.ulpin || '')}
        />
        {lookupUlpin && (
          <div className="mt-3">
            {lookupQ.isLoading && <div className="text-xs text-slate-500">Looking up…</div>}
            {lookupQ.isError && (
              <div className="text-xs text-red-600">
                No unit found for <span className="font-mono">{lookupUlpin}</span>.
              </div>
            )}
            {lookupQ.unit && (
              <ULPINCard
                ulpin={lookupQ.unit.unit_ulpin || lookupQ.unit.ulpin}
                unitType={lookupQ.unit.unit_type}
                ownerName={lookupQ.unit.owner_name}
                area={lookupQ.unit.area_sqm}
                volume={lookupQ.unit.volume_cubm}
                status={lookupQ.unit.status}
                rightsType={lookupQ.unit.rights_type || 'full_ownership'}
                parcelId={lookupQ.unit.parent_parcel_id}
                unitId={lookupQ.unit.unit_id || lookupQ.unit.id}
              />
            )}
          </div>
        )}
      </div>

      <div className="card p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-800">ULPIN Registry</h2>
          <div className="flex items-center gap-2">
            <select className="input w-auto" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">All unit types</option>
              {unitTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <button type="button" className="btn-secondary" onClick={exportCsv} disabled={!filtered.length}>
              Export CSV
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="text-sm text-slate-500">Loading registry…</div>
        ) : isError ? (
          <div className="text-sm text-slate-500">
            Registry unavailable — the backend may not be running yet.
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-sm text-slate-500">
            No units registered yet. Upload data and run the pipeline to generate 3D ULPINs.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-slate-400">
                  <th className="pb-2">ULPIN</th>
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Floor</th>
                  <th className="pb-2">Area (m²)</th>
                  <th className="pb-2">Volume (m³)</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.unit_id || u.id} className="border-t border-slate-100 hover:bg-brand-50/50">
                    <td className="py-2 font-mono text-xs text-brand-700">
                      {u.unit_ulpin || u.ulpin || '—'}
                    </td>
                    <td className="py-2">
                      <span className={`badge ${OWNERSHIP_BADGES[u.rights_type] || 'bg-slate-100 text-slate-700'} capitalize`}>
                        {OWNERSHIP_LABELS[u.rights_type] || u.unit_type}
                      </span>
                    </td>
                    <td className="py-2 text-xs">{(u.floor_label || u.floor_number) ?? '—'}</td>
                    <td className="py-2 text-xs">{u.area_sqm != null ? Number(u.area_sqm).toFixed(2) : '—'}</td>
                    <td className="py-2 text-xs">{u.volume_cubm != null ? Number(u.volume_cubm).toFixed(2) : '—'}</td>
                    <td className="py-2">
                      <span className={`badge ${PARCEL_STATUS_STYLES[u.status] || 'bg-slate-100 text-slate-700'}`}>
                        {u.status || 'draft'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
