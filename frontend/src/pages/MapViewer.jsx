// MapViewer.jsx — REALISTIC MULTI-FLOOR BUILDINGS WITH FLOOR EXPLOSION
// Per-floor extruded units, floor-peel slider, hover highlight, selected
// building floor panel with ULPINs.
import { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import client from '../api/client.js';
import { isPlaceholderToken } from '../utils/constants.js';

window.CESIUM_BASE_URL = window.CESIUM_BASE_URL || '/cesium/';

export default function MapViewer() {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const buildingsRef = useRef([]); // read from Cesium handlers (no stale closure)
  const floorPeelRef = useRef(100); // read inside CallbackProperty (must be a ref)
  const hoveredRef = useRef(null); // hover state inside MOUSE_MOVE handler
  const [searchQuery, setSearchQuery] = useState('');
  const [buildings, setBuildings] = useState([]);
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [selectedBuildingUnits, setSelectedBuildingUnits] = useState([]);
  const [floorPeel, setFloorPeel] = useState(100); // Show all floors by default
  const [loading, setLoading] = useState(false);

  // World terrain needs a real Cesium Ion token; with the placeholder token
  // we run on the ellipsoid with OpenStreetMap imagery instead.
  const cesiumToken = import.meta.env.VITE_CESIUM_TOKEN;
  const hasCesiumToken = !isPlaceholderToken(cesiumToken);

  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return undefined;

    let viewer;
    try {
      if (hasCesiumToken) {
        Cesium.Ion.defaultAccessToken = cesiumToken;
      }
      viewer = new Cesium.Viewer(containerRef.current, {
        ...(hasCesiumToken
          ? { terrainProvider: Cesium.createWorldTerrain() }
          : {
              baseLayer: new Cesium.ImageryLayer(
                new Cesium.UrlTemplateImageryProvider({
                  url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  credit: '© OpenStreetMap contributors',
                }),
              ),
            }),
        timeline: false,
        animation: false,
        baseLayerPicker: hasCesiumToken,
        geocoder: false, // we build our own
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        infoBox: false,
        selectionIndicator: false,
      });
      viewerRef.current = viewer;

      viewer.scene.globe.enableLighting = true;
      viewer.scene.globe.depthTestAgainstTerrain = false;

      // Start over India
      viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(78.9629, 20.5937, 6000000),
      });

      // CLICK: Select building and show floor details
      viewer.screenSpaceEventHandler.setInputAction((click) => {
        const picked = viewer.scene.pick(click.position);
        if (Cesium.defined(picked) && Cesium.defined(picked.id)) {
          const bId = picked.id.properties?.building_id?.getValue();
          if (bId) {
            selectBuildingById(bId);
          }
        } else {
          setSelectedBuilding(null);
          setSelectedBuildingUnits([]);
          resetBuildingHighlights(viewer);
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

      // HOVER: Highlight building on mouse over (ref-based: the handler is
      // registered once and must see the current hover state)
      viewer.screenSpaceEventHandler.setInputAction((move) => {
        const picked = viewer.scene.pick(move.endPosition);
        let bId = null;
        if (Cesium.defined(picked) && Cesium.defined(picked.id)) {
          bId = picked.id.properties?.building_id?.getValue() ?? null;
        }
        if (bId !== hoveredRef.current) {
          if (hoveredRef.current) highlightBuilding(viewer, hoveredRef.current, false);
          hoveredRef.current = bId;
          if (bId) highlightBuilding(viewer, bId, true);
        }
      }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

      loadBuildings(viewer);
    } catch (err) {
      console.error('3D viewer failed to start:', err);
    }

    return () => {
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
      viewerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasCesiumToken, cesiumToken]);

  // Fetch buildings and their units
  async function loadBuildings(viewer) {
    try {
      const res = await client.get('/buildings', { params: { limit: 500 } });
      const buildingData = res.data || [];
      console.log('[MapViewer] loaded buildings:', buildingData.length);

      const buildingsWithUnits = [];
      for (const b of buildingData) {
        try {
          const uRes = await client.get(`/buildings/${b.building_id}/units`);
          buildingsWithUnits.push({ ...b, units: uRes.data || [] });
        } catch (e) {
          console.warn('[MapViewer] failed to load units for building', b.building_id, e);
          buildingsWithUnits.push({ ...b, units: [] });
        }
      }

      buildingsRef.current = buildingsWithUnits;
      setBuildings(buildingsWithUnits);
      renderBuildings(viewer, buildingsWithUnits);

      // Fly to first building
      if (buildingsWithUnits[0]?.units?.length > 0) {
        setTimeout(() => {
          flyToBuilding(viewer, buildingsWithUnits[0].building_id);
        }, 1500);
      }
    } catch (e) {
      console.error('[MapViewer] load failed:', e);
    }
  }

  function renderBuildings(viewer, buildingData) {
    viewer.entities.removeAll();
    let entityCount = 0;

    buildingData.forEach((b) => {
      const baseColor = b.metadata?.cesium_color || '#2E86AB';
      const outlineColor = b.metadata?.cesium_outline || '#A8DADC';
      const totalFloors = b.floors_above_ground || 1;

      // Sort units by floor
      const sortedUnits = [...(b.units || [])].sort(
        (a, c) => (a.floor_number || 0) - (c.floor_number || 0),
      );

      sortedUnits.forEach((u) => {
        // Prefer the unit's own subdivided footprint (bottom ring of its 3D
        // volume); fall back to the whole-building footprint.
        const coords = parseVolumeCoords(u.volume_3d) || parseFootprintCoords(b.footprint);
        if (!coords || coords.length < 4) {
          console.warn('[MapViewer] skipping unit with invalid geometry:', u.unit_id);
          return;
        }

        const flat = coords.flatMap((c) => [c.lon, c.lat]);
        const positions = Cesium.Cartesian3.fromDegreesArray(flat);

        // Floor height positioning
        const zBottom = u.height_min_m ?? (u.floor_number - 1) * 3;
        const zTop = u.height_max_m ?? u.floor_number * 3;

        // Color: vary by floor number for visual distinction
        // Ground floor = darker, top floor = lighter
        const floorRatio = totalFloors > 1 ? (u.floor_number - 1) / (totalFloors - 1) : 0;
        const floorColor = adjustColorByFloor(baseColor, floorRatio);

        viewer.entities.add({
          id: `unit-${u.unit_id}`,
          name: `${b.building_name} — ${u.floor_label}`,
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(positions),
            extrudedHeight: zTop,
            height: zBottom,
            material: new Cesium.ColorMaterialProperty(
              new Cesium.CallbackProperty(() => {
                // Floor peel: hide floors above the slider level.
                // floorPeelRef keeps this live; a state variable would be stale.
                if (floorPeelRef.current < u.floor_number * 10) {
                  return Cesium.Color.fromCssColorString(floorColor).withAlpha(0.08);
                }
                return Cesium.Color.fromCssColorString(floorColor).withAlpha(0.9);
              }, false),
            ),
            outline: true,
            outlineColor: Cesium.Color.fromCssColorString(outlineColor),
            outlineWidth: 2,
            shadows: Cesium.ShadowMode.ENABLED,
          },
          properties: {
            building_id: b.building_id,
            building_name: b.building_name,
            unit_id: u.unit_id,
            unit_ulpin: u.unit_ulpin,
            floor_label: u.floor_label,
            floor_number: u.floor_number,
            unit_type: u.unit_type,
            height_min: zBottom,
            height_max: zTop,
            area_sqm: u.area_sqm,
            owner_name: b.owner_name || 'Government of Maharashtra',
            base_color: baseColor,
            outline_color: outlineColor,
          },
        });
        entityCount += 1;
      });

      // Building label at top
      if (sortedUnits.length > 0) {
        const topUnit = sortedUnits[sortedUnits.length - 1];
        const labelCoords = parseFootprintCoords(b.footprint);
        if (labelCoords && labelCoords.length >= 2) {
          viewer.entities.add({
            id: `label-${b.building_id}`,
            position: Cesium.Cartesian3.fromDegrees(
              labelCoords[0].lon,
              labelCoords[0].lat,
              (topUnit.height_max_m || 30) + 8,
            ),
            label: {
              text: b.building_name.split(' — ')[1] || b.building_name,
              font: 'bold 13px sans-serif',
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 3,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0, -8),
              showBackground: true,
              backgroundColor: Cesium.Color.fromCssColorString(baseColor).withAlpha(0.8),
              backgroundPadding: new Cesium.Cartesian2(8, 4),
            },
          });
        }
      }
    });

    console.log(`[MapViewer] rendered ${entityCount} unit entities across ${buildingData.length} buildings`);
  }

  // Parse the unit's 3D volume WKT to its bottom-face ring.
  // ST_AsText emits `(((x y z,...)))` — strip parens so Number() never sees them.
  function parseVolumeCoords(volumeWkt) {
    if (!volumeWkt || typeof volumeWkt !== 'string') return null;
    try {
      const match = volumeWkt.match(/\(\(([^)]+)\)\)/);
      if (!match) return null;
      const ring = match[1].replace(/[()]/g, '');
      const coords = ring.split(',').map((p) => {
        const [lon, lat, z] = p.trim().split(/\s+/).map(Number);
        return { lon, lat, z };
      });
      if (coords.some((c) => !Number.isFinite(c.lon) || !Number.isFinite(c.lat))) return null;
      return coords;
    } catch (e) {
      return null;
    }
  }

  // Fallback: building footprint WKT → [{lon, lat}, ...]
  function parseFootprintCoords(footprintWkt) {
    if (!footprintWkt || typeof footprintWkt !== 'string') return null;
    try {
      const match = footprintWkt.match(/\(\(([^)]+)\)\)/);
      if (!match) return null;
      return match[1].split(',').map((p) => {
        const [lon, lat] = p.trim().split(/\s+/).map(Number);
        return { lon, lat };
      });
    } catch (e) {
      return null;
    }
  }

  function adjustColorByFloor(baseHex, ratio) {
    // Make ground floor darker, upper floors lighter
    const num = parseInt(baseHex.replace('#', ''), 16);
    const factor = 1 - ratio * 0.4; // 1.0 to 0.6
    const R = Math.round(((num >> 16) & 0xff) * factor);
    const G = Math.round(((num >> 8) & 0xff) * factor);
    const B = Math.round((num & 0xff) * factor);
    return `rgb(${R},${G},${B})`;
  }

  function highlightBuilding(viewer, buildingId, isHighlight) {
    viewer.entities.values.forEach((e) => {
      if (e.id?.startsWith('unit-') && e.properties?.building_id?.getValue() === buildingId) {
        if (e.polygon) {
          e.polygon.outlineWidth = isHighlight ? 4 : 2;
          e.polygon.outlineColor = isHighlight
            ? Cesium.Color.YELLOW
            : Cesium.Color.fromCssColorString(e.properties.outline_color?.getValue() || '#FFFFFF');
        }
      }
    });
  }

  function resetBuildingHighlights(viewer) {
    viewer.entities.values.forEach((e) => {
      if (e.id?.startsWith('unit-') && e.polygon) {
        e.polygon.outlineWidth = 2;
        const outlineColor = e.properties?.outline_color?.getValue() || '#FFFFFF';
        e.polygon.outlineColor = Cesium.Color.fromCssColorString(outlineColor);
      }
    });
  }

  function selectBuildingById(buildingId) {
    const b = buildingsRef.current.find((x) => x.building_id === buildingId);
    if (!b) return;

    setSelectedBuilding(b);
    setSelectedBuildingUnits(b.units || []);
    setFloorPeel(b.floors_above_ground * 10 + 10);
    floorPeelRef.current = b.floors_above_ground * 10 + 10;

    const viewer = viewerRef.current;
    if (viewer) {
      resetBuildingHighlights(viewer);
      highlightBuilding(viewer, buildingId, true);

      const firstUnit = b.units?.[0];
      if (firstUnit) {
        const entity = viewer.entities.getById(`unit-${firstUnit.unit_id}`);
        if (entity) {
          viewer.flyTo(entity, {
            duration: 1.5,
            offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-40), 350),
          });
        }
      }
    }
  }

  function flyToBuilding(viewer, buildingId) {
    const b = buildingsRef.current.find((x) => x.building_id === buildingId);
    if (!b || !b.units?.length) return;

    const firstUnit = b.units[0];
    const entity = viewer.entities.getById(`unit-${firstUnit.unit_id}`);
    if (entity) {
      viewer.flyTo(entity, {
        duration: 1.5,
        offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-35), 300),
      });
    }
  }

  // Search (Nominatim — free OpenStreetMap geocoder, no API key)
  async function handleSearch(e) {
    e?.preventDefault();
    if (!searchQuery.trim()) return;
    setLoading(true);
    const viewer = viewerRef.current;
    if (!viewer) {
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&countrycodes=in&limit=5`,
        { headers: { 'User-Agent': '3D-ULPIN-App/1.0' } },
      );
      const results = await res.json();
      setLoading(false);
      if (results?.length > 0) {
        const { lon, lat } = results[0];
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(parseFloat(lon), parseFloat(lat), 5000),
          duration: 2,
        });
      } else {
        alert('Location not found. Try a different name.');
      }
    } catch {
      setLoading(false);
      alert('Search failed. Check internet connection.');
    }
  }

  return (
    <div className="relative -m-4 h-full w-full">
      {/* SEARCH BAR */}
      <form
        onSubmit={handleSearch}
        style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 1000, width: 420, maxWidth: '90vw', background: 'white', borderRadius: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.25)', padding: '4px 8px',
          display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        <span style={{ marginLeft: 8, fontSize: 18 }}>🔍</span>
        <input
          type="text"
          placeholder="Search city, district..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            flex: 1, border: 'none', outline: 'none', padding: '10px 4px',
            fontSize: 15, background: 'transparent',
          }}
        />
        <button
          type="submit"
          style={{
            background: '#008cff', color: 'white', border: 'none', borderRadius: 20,
            padding: '8px 18px', cursor: 'pointer', fontWeight: 600,
          }}
        >
          Search
        </button>
      </form>

      {/* BUILDING LIST SIDEBAR */}
      <div
        style={{
          position: 'absolute', right: 12, top: 70, zIndex: 1000, width: 300,
          background: 'rgba(255,255,255,0.95)', borderRadius: 12,
          boxShadow: '0 4px 16px rgba(0,0,0,0.15)', maxHeight: '40vh', overflowY: 'auto',
        }}
      >
        <div
          style={{
            padding: '14px', fontWeight: 'bold', fontSize: 15, background: '#f8f9fa',
            borderRadius: '12px 12px 0 0', borderBottom: '1px solid #e0e0e0',
          }}
        >
          🏛️ Government Buildings ({buildings.length})
        </div>
        {buildings.map((b) => {
          const color = b.metadata?.cesium_color || '#2E86AB';
          const isSelected = selectedBuilding?.building_id === b.building_id;
          return (
            <div
              key={b.building_id}
              onClick={() => selectBuildingById(b.building_id)}
              style={{
                padding: '10px 14px', cursor: 'pointer', fontSize: 13,
                borderBottom: '1px solid #f0f0f0',
                background: isSelected ? '#e3f2fd' : 'white',
                borderLeft: `4px solid ${color}`,
              }}
              onMouseEnter={(e) => {
                if (!isSelected) e.currentTarget.style.background = '#f5f5f5';
              }}
              onMouseLeave={(e) => {
                if (!isSelected) e.currentTarget.style.background = 'white';
              }}
            >
              <div style={{ fontWeight: 600, color: '#1a1a2e', fontSize: 13 }}>{b.building_name}</div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                {b.floors_above_ground} floors • {b.building_type} • {b.units?.length || 0} units
              </div>
            </div>
          );
        })}
      </div>

      {/* SELECTED BUILDING FLOOR PANEL */}
      {selectedBuilding && (
        <div
          style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            zIndex: 1000, width: 320,
            background: 'rgba(255,255,255,0.97)', borderRadius: 16,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)', maxHeight: '60vh', overflowY: 'auto',
            border: '2px solid #008cff',
          }}
        >
          <div style={{ padding: '16px', background: '#008cff', color: 'white', borderRadius: '14px 14px 0 0' }}>
            <div style={{ fontWeight: 'bold', fontSize: 15 }}>{selectedBuilding.building_name}</div>
            <div style={{ fontSize: 12, marginTop: 4, opacity: 0.9 }}>
              {selectedBuilding.floors_above_ground} floors • {selectedBuildingUnits.length} units
            </div>
            <button
              onClick={() => {
                setSelectedBuilding(null);
                setSelectedBuildingUnits([]);
              }}
              style={{
                position: 'absolute', top: 12, right: 12, background: 'rgba(255,255,255,0.2)',
                border: 'none', color: 'white', borderRadius: '50%', width: 28, height: 28,
                cursor: 'pointer', fontSize: 16,
              }}
            >
              ✕
            </button>
          </div>

          <div style={{ padding: '12px 16px', borderBottom: '1px solid #e0e0e0' }}>
            <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>Floor Peel (hide upper floors)</div>
            <input
              type="range"
              min={10}
              max={selectedBuilding.floors_above_ground * 10 + 10}
              value={floorPeel}
              onChange={(e) => {
                const v = Number(e.target.value);
                setFloorPeel(v);
                floorPeelRef.current = v; // CallbackProperty reads the ref live
              }}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: 11, color: '#888', textAlign: 'center', marginTop: 4 }}>
              {floorPeel >= selectedBuilding.floors_above_ground * 10
                ? 'Showing all floors'
                : `Showing floors up to level ${Math.floor(floorPeel / 10)}`}
            </div>
          </div>

          <div style={{ padding: '8px 0' }}>
            {[...selectedBuildingUnits].reverse().map((u) => (
              <div
                key={u.unit_id}
                style={{
                  padding: '12px 16px', borderBottom: '1px solid #f0f0f0',
                  background: u.floor_number % 2 === 0 ? '#fafafa' : 'white',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <div
                    style={{
                      width: 32, height: 32, borderRadius: '50%',
                      background: '#008cff', color: 'white', display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                      fontWeight: 'bold', fontSize: 12,
                    }}
                  >
                    F{u.floor_number}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#1a1a2e' }}>
                      {String(u.unit_type || '').toUpperCase()}
                    </div>
                    <div style={{ fontSize: 11, color: '#888' }}>{u.floor_label}</div>
                  </div>
                </div>

                <div
                  style={{
                    background: '#f0f8ff', padding: '8px 12px', borderRadius: 8,
                    fontFamily: 'monospace', fontSize: 12, color: '#008cff',
                    border: '1px dashed #008cff', marginBottom: 6,
                    wordBreak: 'break-all',
                  }}
                >
                  {u.unit_ulpin}
                </div>

                <div style={{ fontSize: 11, color: '#555', lineHeight: 1.5 }}>
                  <div><strong>Height:</strong> {u.height_min_m}m — {u.height_max_m}m</div>
                  <div><strong>Area:</strong> {u.area_sqm} m²</div>
                  <div><strong>Volume:</strong> {u.volume_cubm} m³</div>
                  <div><strong>Owner:</strong> {selectedBuilding.owner_name || 'Government of Maharashtra'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CATEGORY LEGEND */}
      <div
        style={{
          position: 'absolute', left: 12, bottom: 24, zIndex: 1000,
          background: 'rgba(255,255,255,0.9)', padding: '12px 16px', borderRadius: 10,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)', fontSize: 12,
        }}
      >
        <div style={{ fontWeight: 'bold', marginBottom: 8, fontSize: 13 }}>Building Types</div>
        {[
          { c: '#2E86AB', l: 'Residential' },
          { c: '#9B5DE5', l: 'Commercial' },
          { c: '#E63946', l: 'Government' },
          { c: '#6C757D', l: 'Industrial' },
          { c: '#0077B6', l: 'Infrastructure' },
        ].map((item) => (
          <div key={item.l} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <div style={{ width: 14, height: 14, background: item.c, borderRadius: 3 }} />
            <span>{item.l}</span>
          </div>
        ))}
      </div>

      {/* STATUS */}
      <div
        style={{
          position: 'absolute', bottom: 24, right: 320, zIndex: 1000,
          background: 'rgba(0,0,0,0.7)', color: 'white', padding: '8px 14px',
          borderRadius: 8, fontSize: 13,
        }}
      >
        {buildings.length > 0
          ? `📍 ${buildings.length} public buildings • ${buildings.reduce((a, b) => a + (b.units?.length || 0), 0)} units`
          : '🔍 Loading...'}
      </div>

      {/* LOADING */}
      {loading && (
        <div
          style={{
            position: 'absolute', top: 65, left: '50%', transform: 'translateX(-50%)',
            zIndex: 1000, background: 'white', padding: '8px 16px', borderRadius: 8,
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
          }}
        >
          Searching...
        </div>
      )}

      {/* CESIUM CONTAINER */}
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
    </div>
  );
}
