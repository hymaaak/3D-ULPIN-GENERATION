// Copies Cesium's static build output (workers, widgets, assets) into
// public/cesium so the dev server / built app can serve them at /cesium/.
// Cesium needs CESIUM_BASE_URL=/cesium/ at runtime (set in MapViewer).
import { cpSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, 'node_modules', 'cesium', 'Build', 'Cesium');
const dest = join(root, 'public', 'cesium');

if (existsSync(src)) {
  mkdirSync(dirname(dest), { recursive: true });
  cpSync(src, dest, { recursive: true });
  console.log('[copy-cesium] copied Cesium static assets to public/cesium');
} else {
  console.warn('[copy-cesium] node_modules/cesium not found yet — skipping (run after npm install)');
}
