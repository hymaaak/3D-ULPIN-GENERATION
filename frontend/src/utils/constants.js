// Shared constants + small geometry/env helpers for the 3D ULPIN frontend.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// ---------------------------------------------------------------------------
// AI pipeline steps (spec section 10, JobMonitor)
// ---------------------------------------------------------------------------
export const PIPELINE_STEPS = [
  { key: 'upload', label: 'Upload' },
  { key: 'extract', label: 'Extract' },
  { key: 'segment', label: 'Segment' },
  { key: 'delineate', label: 'Delineate' },
  { key: 'validate', label: 'Validate' },
  { key: 'ulpin', label: 'ULPIN' },
  { key: 'done', label: 'Done' },
];

// Map free-form backend step names onto PIPELINE_STEPS keys.
const STEP_ALIASES = {
  uploaded: 'upload',
  upload: 'upload',
  queued: 'upload',
  extracting: 'extract',
  extraction: 'extract',
  building_extraction: 'extract',
  segmenting: 'segment',
  segmentation: 'segment',
  floor_segmentation: 'segment',
  delineating: 'delineate',
  delineation: 'delineate',
  vertical_delineation: 'delineate',
  validating: 'validate',
  validation: 'validate',
  topology_validation: 'validate',
  ulpin_generation: 'ulpin',
  generating_ulpin: 'ulpin',
  conflict_detection: 'done',
  completed: 'done',
  done: 'done',
};

export function normalizeStep(step) {
  if (!step) return null;
  return STEP_ALIASES[String(step).toLowerCase()] || null;
}

// ---------------------------------------------------------------------------
// Source types (spec section 6 enum) + extension-based auto-detection
// ---------------------------------------------------------------------------
export const SOURCE_TYPES = {
  drone_image: { label: 'Drone Imagery', exts: ['.tif', '.tiff'] },
  lidar: { label: 'LiDAR Point Cloud', exts: ['.laz', '.las'] },
  gis_shapefile: { label: 'GIS Shapefile', exts: ['.shp', '.geojson', '.json'] },
  floor_plan: { label: 'Building Plan', exts: ['.dwg', '.dxf', '.ifc'] },
};

export function detectSourceType(filename) {
  const lower = String(filename || '').toLowerCase();
  for (const [key, cfg] of Object.entries(SOURCE_TYPES)) {
    if (cfg.exts.some((ext) => lower.endsWith(ext))) return key;
  }
  return 'drone_image';
}

// ---------------------------------------------------------------------------
// Colors / badges
// ---------------------------------------------------------------------------
export const OWNERSHIP_COLORS = {
  full_ownership: '#2563eb',
  lease: '#16a34a',
  easement: '#d97706',
  air_right: '#9333ea',
  subsurface: '#dc2626',
  joint: '#0891b2',
  default: '#64748b',
};

export function ownershipColor(rightsType) {
  return OWNERSHIP_COLORS[rightsType] || OWNERSHIP_COLORS.default;
}

export const OWNERSHIP_BADGES = {
  full_ownership: 'bg-blue-100 text-blue-800',
  lease: 'bg-green-100 text-green-800',
  easement: 'bg-amber-100 text-amber-800',
  air_right: 'bg-purple-100 text-purple-800',
  subsurface: 'bg-red-100 text-red-800',
  joint: 'bg-cyan-100 text-cyan-800',
};

export const OWNERSHIP_LABELS = {
  full_ownership: 'Full Ownership',
  lease: 'Lease',
  easement: 'Easement',
  air_right: 'Air Right',
  subsurface: 'Subsurface',
  joint: 'Joint',
};

export const SEVERITY_STYLES = {
  low: 'bg-emerald-100 text-emerald-800',
  medium: 'bg-amber-100 text-amber-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

export const CONFLICT_TYPES = {
  overlap: '3D Overlap',
  gap: 'Gap',
  boundary_mismatch: 'Boundary Mismatch',
  air_right_violation: 'Air Right Violation',
  utility_intrusion: 'Utility Intrusion',
  ownership_dispute: 'Ownership Dispute',
};

export const PARCEL_TYPE_COLORS = {
  surface: '#22c55e',
  multi_storey: '#2563eb',
  underground: '#7c3aed',
  air_right: '#db2777',
  mixed: '#ea580c',
};

export const PARCEL_TYPE_LABELS = {
  surface: 'Surface',
  multi_storey: 'Multi-Storey',
  underground: 'Underground',
  air_right: 'Air Right',
  mixed: 'Mixed',
};

export const PARCEL_STATUS_STYLES = {
  draft: 'bg-slate-100 text-slate-700',
  verified: 'bg-emerald-100 text-emerald-800',
  disputed: 'bg-red-100 text-red-800',
  archived: 'bg-slate-200 text-slate-500',
};

export const JOB_STATUS_STYLES = {
  pending: 'bg-slate-100 text-slate-700',
  running: 'bg-blue-100 text-blue-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-slate-200 text-slate-500',
};

export const JOB_TYPE_LABELS = {
  building_extraction: 'Building Extraction',
  floor_segmentation: 'Floor Segmentation',
  vertical_delineation: 'Vertical Delineation',
  topology_validation: 'Topology Validation',
  ulpin_generation: 'ULPIN Generation',
  conflict_detection: 'Conflict Detection',
};

// ---------------------------------------------------------------------------
// Token handling — VITE_* tokens may be missing or placeholder strings on
// first run. Never crash: detect placeholders and degrade gracefully.
// ---------------------------------------------------------------------------
export function isPlaceholderToken(token) {
  if (!token || typeof token !== 'string') return true;
  const t = token.trim().toLowerCase();
  if (t.length < 8) return true;
  return /your|here|placeholder|xxx|changeme|token_here/.test(t);
}

// ---------------------------------------------------------------------------
// Geometry helpers — backend may return GeoJSON objects or coordinate arrays.
// ---------------------------------------------------------------------------

// Accepts GeoJSON Polygon/MultiPolygon, {coordinates}, a raw coordinate ring
// array, or a GeoJSON geometry string; returns [ [lon,lat], ... ] or null.
export function coordsFromGeometry(geom) {
  if (!geom) return null;
  let g = geom;
  if (typeof g === 'string') {
    try {
      g = JSON.parse(g);
    } catch {
      return null;
    }
  }
  let ring = null;
  if (Array.isArray(g)) ring = g;
  else if (Array.isArray(g.coordinates)) {
    if (g.type === 'Polygon') ring = g.coordinates[0];
    else if (g.type === 'MultiPolygon') ring = g.coordinates[0]?.[0];
    else if (g.type === 'Point') ring = null;
  } else if (g.geometry) {
    return coordsFromGeometry(g.geometry);
  } else if (g.footprint) {
    return coordsFromGeometry(g.footprint);
  } else if (g.geom_2d) {
    return coordsFromGeometry(g.geom_2d);
  }
  if (!ring || ring.length < 3) return null;
  return ring.map((c) => [Number(c[0]), Number(c[1])]).filter((c) => Number.isFinite(c[0]) && Number.isFinite(c[1]));
}

export function polygonCenter(coords) {
  if (!coords || !coords.length) return [72.8777, 19.076];
  const n = coords.length;
  const lon = coords.reduce((s, c) => s + c[0], 0) / n;
  const lat = coords.reduce((s, c) => s + c[1], 0) / n;
  return [lon, lat];
}

// Normalize a list-style API response ({items: []} | {results: []} | array).
export function asList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

// ---------------------------------------------------------------------------
// Demo fallback data (Mumbai) — used by MapViewer when the backend has no
// buildings yet so the hero viewer always renders something.
// ---------------------------------------------------------------------------
export const DEMO_CENTER = [72.8777, 19.076];

function demoFootprint(lon, lat, size) {
  return [
    [lon, lat],
    [lon + size, lat],
    [lon + size, lat + size],
    [lon, lat + size],
    [lon, lat],
  ];
}

export const DEMO_PARCELS = [
  {
    parcel_id: 'demo-p1',
    ulpin: '3D-ULPIN-27-023-456789-0001-F00-U00-00',
    parcel_type: 'multi_storey',
    status: 'verified',
    area_sqm: 1234.56,
    geom_2d: { type: 'Polygon', coordinates: [demoFootprint(72.8765, 19.0752, 0.0012)] },
  },
  {
    parcel_id: 'demo-p2',
    ulpin: '3D-ULPIN-27-023-456789-0002-F00-U00-00',
    parcel_type: 'surface',
    status: 'verified',
    area_sqm: 980.1,
    geom_2d: { type: 'Polygon', coordinates: [demoFootprint(72.8782, 19.0755, 0.001)] },
  },
  {
    parcel_id: 'demo-p3',
    ulpin: '3D-ULPIN-27-023-456789-0003-F00-U00-00',
    parcel_type: 'mixed',
    status: 'draft',
    area_sqm: 2100.0,
    geom_2d: { type: 'Polygon', coordinates: [demoFootprint(72.877, 19.077, 0.0014)] },
  },
];

export const DEMO_BUILDINGS = [
  {
    building_id: 'demo-b1',
    parcel_id: 'demo-p1',
    building_name: 'Tower A (ML-extracted)',
    height_m: 45,
    floors_above_ground: 12,
    floors_below_ground: 2,
    building_type: 'residential',
    confidence_score: 0.94,
    layer: 'building',
    ownership_type: 'full_ownership',
    ulpin: '3D-ULPIN-27-023-456789-0001-F05-U01-82',
    owner_name: 'Ramesh Patel',
    footprint: { type: 'Polygon', coordinates: [demoFootprint(72.8767, 19.0754, 0.0008)] },
  },
  {
    building_id: 'demo-b2',
    parcel_id: 'demo-p1',
    building_name: 'Basement Parking B2',
    height_m: 6,
    floors_below_ground: 2,
    building_type: 'infrastructure',
    confidence_score: 0.88,
    layer: 'underground',
    ownership_type: 'subsurface',
    ulpin: '3D-ULPIN-27-023-456789-0001-F-2-U01-71',
    owner_name: 'Skyline Developers Pvt Ltd',
    footprint: { type: 'Polygon', coordinates: [demoFootprint(72.87675, 19.07545, 0.0007)] },
  },
  {
    building_id: 'demo-b3',
    parcel_id: 'demo-p3',
    building_name: 'Air Rights Podium',
    height_m: 12,
    floors_above_ground: 2,
    building_type: 'commercial',
    confidence_score: 0.81,
    layer: 'air',
    ownership_type: 'air_right',
    ulpin: '3D-ULPIN-27-023-456789-0003-F12-U01-33',
    owner_name: 'Mumbai Metro Rail Corp',
    footprint: { type: 'Polygon', coordinates: [demoFootprint(72.8772, 19.0772, 0.0009)] },
  },
];
