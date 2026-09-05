import { Link, useParams } from 'react-router-dom';
import { useParcel, useParcelBuildings, useBuildingUnits } from '../hooks/useParcels.js';
import { useQuery } from '@tanstack/react-query';
import * as unitsApi from '../api/units.js';
import ULPINCard from '../components/ULPINCard.jsx';
import { PARCEL_STATUS_STYLES, PARCEL_TYPE_LABELS } from '../utils/constants.js';

// Units of one building, each rendering ULPIN cards. Split into its own
// component so the per-building query hook stays unconditional.
function BuildingSection({ building }) {
  const { units, isLoading } = useBuildingUnits(building.building_id || building.id);
  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">
            {building.building_name || `Building ${String(building.building_id || building.id).slice(0, 8)}`}
          </h3>
          <div className="text-xs text-slate-500">
            {building.building_type} · {building.floors_above_ground ?? 0} floors above /{' '}
            {building.floors_below_ground ?? 0} below
            {building.extracted_by_ml && ' · ML-extracted'}
            {building.confidence_score != null &&
              ` · ${(building.confidence_score * 100).toFixed(0)}% confidence`}
          </div>
        </div>
      </div>
      {isLoading ? (
        <div className="mt-3 text-xs text-slate-500">Loading units…</div>
      ) : units.length === 0 ? (
        <div className="mt-3 text-xs text-slate-500">No 3D units delineated yet.</div>
      ) : (
        <div className="mt-3 grid gap-3 xl:grid-cols-2">
          {units.map((u) => (
            <UnitCard key={u.unit_id || u.id} unit={u} building={building} />
          ))}
        </div>
      )}
    </div>
  );
}

function UnitCard({ unit, building }) {
  const ownershipQ = useQuery({
    queryKey: ['unit-ownership', unit.unit_id || unit.id],
    queryFn: () => unitsApi.getUnitOwnership(unit.unit_id || unit.id),
    enabled: Boolean(unit.unit_id || unit.id),
    retry: false,
  });
  const owners = Array.isArray(ownershipQ.data)
    ? ownershipQ.data
    : ownershipQ.data?.items || ownershipQ.data?.results || [];
  const current = owners[0];

  return (
    <ULPINCard
      ulpin={unit.unit_ulpin || unit.ulpin}
      unitType={unit.unit_type}
      ownerName={current?.owner?.name || current?.owner_name || unit.owner_name}
      area={unit.area_sqm}
      volume={unit.volume_cubm}
      status={unit.status}
      rightsType={current?.rights_type || unit.rights_type || 'full_ownership'}
      parcelId={building.parcel_id}
      unitId={unit.unit_id || unit.id}
    />
  );
}

export default function ParcelDetail() {
  const { id } = useParams();
  const { parcel, isLoading, isError } = useParcel(id);
  const { buildings } = useParcelBuildings(id);

  if (isLoading) {
    return <div className="text-sm text-slate-500">Loading parcel…</div>;
  }
  if (isError || !parcel) {
    return (
      <div className="card max-w-md p-6">
        <div className="text-sm font-semibold text-red-600">Parcel not found</div>
        <div className="mt-1 text-xs text-slate-500">
          The parcel may not exist or the backend is unreachable.
        </div>
        <Link to="/" className="btn-secondary mt-4">Back to dashboard</Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-mono text-base font-semibold text-brand-700">{parcel.ulpin}</h2>
          {parcel.parcel_type && (
            <span className="badge bg-brand-50 text-brand-700">
              {PARCEL_TYPE_LABELS[parcel.parcel_type] || parcel.parcel_type}
            </span>
          )}
          {parcel.status && (
            <span className={`badge ${PARCEL_STATUS_STYLES[parcel.status] || 'bg-slate-100 text-slate-700'}`}>
              {parcel.status}
            </span>
          )}
        </div>
        <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-slate-600 md:grid-cols-4">
          {parcel.legacy_survey_no && <div>Legacy survey no: {parcel.legacy_survey_no}</div>}
          {parcel.village_code && <div>Village code: {parcel.village_code}</div>}
          {parcel.area_sqm != null && <div>Area: {Number(parcel.area_sqm).toFixed(2)} m²</div>}
          {parcel.created_at && <div>Created: {String(parcel.created_at).slice(0, 10)}</div>}
        </div>
        <Link to="/map" className="mt-3 inline-block text-xs font-medium text-brand-600 hover:underline">
          ← Back to 3D map
        </Link>
      </div>

      {buildings.length === 0 ? (
        <div className="card p-4 text-sm text-slate-500">
          No buildings on this parcel yet — run the extraction pipeline from the Upload page.
        </div>
      ) : (
        buildings.map((b) => <BuildingSection key={b.building_id || b.id} building={b} />)
      )}
    </div>
  );
}
