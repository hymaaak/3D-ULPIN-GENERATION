import { useState } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import {
  OWNERSHIP_BADGES,
  OWNERSHIP_LABELS,
  PARCEL_STATUS_STYLES,
} from '../utils/constants.js';

// Display card for a single 3D ULPIN assignment (spec section 10).
export default function ULPINCard({
  ulpin,
  unitType,
  ownerName,
  area,
  volume,
  status,
  rightsType = 'full_ownership',
  parcelId,
  unitId,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(ulpin);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable (non-secure context) — select manually.
      setCopied(false);
    }
  };

  const detailTo = parcelId ? `/parcels/${parcelId}` : unitId ? `/ulpin?q=${encodeURIComponent(ulpin)}` : '/ulpin';

  return (
    <div className="card flex gap-4 p-4">
      <div className="shrink-0 rounded-md border border-slate-200 bg-white p-2">
        {ulpin ? (
          <QRCodeSVG value={ulpin} size={84} level="M" />
        ) : (
          <div className="flex h-[84px] w-[84px] items-center justify-center text-xs text-slate-400">
            No ULPIN
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold text-brand-700">{ulpin || '—'}</span>
          <button
            type="button"
            onClick={handleCopy}
            className="rounded border border-slate-300 px-1.5 py-0.5 text-xs text-slate-600 hover:bg-slate-50"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          <span className={`badge ${OWNERSHIP_BADGES[rightsType] || 'bg-slate-100 text-slate-700'}`}>
            {OWNERSHIP_LABELS[rightsType] || rightsType}
          </span>
          {status && (
            <span className={`badge ${PARCEL_STATUS_STYLES[status] || 'bg-slate-100 text-slate-700'}`}>
              {status}
            </span>
          )}
          {unitType && <span className="badge bg-slate-100 text-slate-700 capitalize">{unitType}</span>}
        </div>
        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600">
          <div>
            Owner: <span className="font-medium text-slate-800">{ownerName || 'Unassigned'}</span>
          </div>
          {area != null && <div>Area: {Number(area).toFixed(2)} m²</div>}
          {volume != null && <div>Volume: {Number(volume).toFixed(2)} m³</div>}
        </div>
        <Link to={detailTo} className="mt-2 inline-block text-xs font-medium text-brand-600 hover:underline">
          View 3D location →
        </Link>
      </div>
    </div>
  );
}
