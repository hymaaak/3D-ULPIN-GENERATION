import { useCallback, useRef, useState } from 'react';
import * as uploadApi from '../api/upload.js';
import * as jobsApi from '../api/jobs.js';
import { detectSourceType, SOURCE_TYPES } from '../utils/constants.js';

// One entry per dropped file with its own upload/trigger lifecycle.
function makeEntry(file) {
  return {
    id: `${file.name}-${file.size}-${file.lastModified}`,
    file,
    name: file.name,
    size: file.size,
    sourceType: detectSourceType(file.name),
    status: 'ready', // ready | uploading | triggering | done | error
    progress: 0,
    error: null,
    sourceId: null,
    jobId: null,
  };
}

const fmtSize = (bytes) =>
  bytes > 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;

export default function UploadPortal({ onJobCreated }) {
  const [entries, setEntries] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const updateEntry = useCallback((id, patch) => {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }, []);

  const addFiles = useCallback((fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    setEntries((prev) => [...prev, ...files.map(makeEntry)]);
  }, []);

  const removeEntry = useCallback((id) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const uploadOne = useCallback(
    async (entry) => {
      updateEntry(entry.id, { status: 'uploading', progress: 0, error: null });
      try {
        // Step 1: presigned URL from the backend.
        const presigned = await uploadApi.getPresignedUrl({
          filename: entry.name,
          contentType: entry.file.type || 'application/octet-stream',
          sourceType: entry.sourceType,
        });

        // Step 2: direct PUT to MinIO.
        const onUploadProgress = (e) => {
          const percent = e.total ? Math.round((e.loaded / e.total) * 100) : 0;
          updateEntry(entry.id, { progress: percent });
        };
        const sourceId = await uploadApi.uploadToPresigned(entry.file, presigned, onUploadProgress);

        // Step 3: trigger the AI pipeline on this source.
        updateEntry(entry.id, { status: 'triggering', progress: 100 });
        const jobPayload = { source_id: sourceId, source_type: entry.sourceType };
        const job = await jobsApi.triggerJob(jobPayload);
        const jobId = job?.job_id || job?.id || job?.jobId || null;

        updateEntry(entry.id, { status: 'done', sourceId, jobId });
        if (jobId && onJobCreated) onJobCreated(jobId);
      } catch (err) {
        const message =
          err?.response?.data?.detail || err?.message || 'Upload failed — is the backend running?';
        updateEntry(entry.id, { status: 'error', error: message });
      }
    },
    [updateEntry, onJobCreated],
  );

  const uploadAll = useCallback(() => {
    entries.filter((e) => e.status === 'ready' || e.status === 'error').forEach(uploadOne);
  }, [entries, uploadOne]);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const anyPending = entries.some((e) => e.status === 'ready' || e.status === 'error');
  const anyActive = entries.some((e) => e.status === 'uploading' || e.status === 'triggering');

  return (
    <div className="card p-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragOver ? 'border-brand-500 bg-brand-50' : 'border-slate-300 hover:border-brand-400'
        }`}
      >
        <div className="text-lg font-medium text-slate-700">
          Drag &amp; drop drone imagery, LiDAR, shapefiles or floor plans
        </div>
        <div className="mt-1 text-sm text-slate-500">
          .tif / .tiff · .laz / .las · .shp / .geojson · .dwg — or click to browse
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </div>

      {entries.length > 0 && (
        <div className="mt-4 space-y-2">
          {entries.map((entry) => (
            <div key={entry.id} className="rounded-md border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-800">{entry.name}</div>
                  <div className="text-xs text-slate-500">
                    {fmtSize(entry.size)} · {SOURCE_TYPES[entry.sourceType]?.label || entry.sourceType}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {entry.status === 'done' && (
                    <span className="badge bg-emerald-100 text-emerald-800">Uploaded</span>
                  )}
                  {(entry.status === 'ready' || entry.status === 'error') && (
                    <button type="button" className="btn-primary" onClick={() => uploadOne(entry)}>
                      {entry.status === 'error' ? 'Retry' : 'Upload'}
                    </button>
                  )}
                  {entry.status !== 'uploading' && entry.status !== 'triggering' && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => removeEntry(entry.id)}
                    >
                      Remove
                    </button>
                  )}
                  {(entry.status === 'uploading' || entry.status === 'triggering') && (
                    <span className="text-xs text-slate-500">
                      {entry.status === 'triggering' ? 'Triggering job…' : `${entry.progress}%`}
                    </span>
                  )}
                </div>
              </div>
              {(entry.status === 'uploading' || entry.status === 'triggering') && (
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full bg-brand-600 transition-all"
                    style={{ width: `${entry.progress}%` }}
                  />
                </div>
              )}
              {entry.error && (
                <div className="mt-2 text-xs text-red-600">{entry.error}</div>
              )}
            </div>
          ))}
          <div className="flex justify-end pt-1">
            <button type="button" className="btn-primary" disabled={!anyPending || anyActive} onClick={uploadAll}>
              Upload all
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
