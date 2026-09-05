import { useCallback, useState } from 'react';

export const MAP_LAYERS = [
  { key: 'surface', label: 'Surface' },
  { key: 'building', label: 'Buildings' },
  { key: 'underground', label: 'Underground' },
  { key: 'air', label: 'Air Rights' },
];

// View state for the MapViewer hero component (view mode + layer toggles).
// Actual Cesium/Mapbox instances live in MapViewer; this hook keeps the
// React-side UI state (sidebar toggles, split/2D/3D mode, selection).
export function useMap() {
  const [viewMode, setViewMode] = useState('3d'); // '3d' | '2d' | 'split'
  const [layers, setLayers] = useState({
    surface: true,
    building: true,
    underground: true,
    air: true,
  });
  const [selected, setSelected] = useState(null);

  const toggleLayer = useCallback((key) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  return {
    viewMode,
    setViewMode,
    layers,
    toggleLayer,
    selected,
    setSelected,
  };
}
