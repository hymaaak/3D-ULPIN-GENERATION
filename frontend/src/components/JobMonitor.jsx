import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import * as jobsApi from '../api/jobs.js';
import { normalizeJob, useJob, useJobSocket } from '../hooks/useJobs.js';
import { JOB_STATUS_STYLES, JOB_TYPE_LABELS, PIPELINE_STEPS } from '../utils/constants.js';

// Real-time pipeline monitor: WebSocket to /ws/jobs/{id} with REST polling
// fallback. Shows the Upload -> Extract -> Segment -> Delineate -> Validate ->
// ULPIN -> Done stepper with per-step progress and confidence score.
export default function JobMonitor({ jobId, onJobChange }) {
  const [liveRaw, setLiveRaw] = useState(null);
  const queryClient = useQueryClient();

  const restQuery = useJob(jobId);
  const socketState = useJobSocket(jobId, (msg) => {
    setLiveRaw(msg);
    const status = String(msg?.status || '').toLowerCase();
    if (status === 'completed' || status === 'failed' || status === 'cancelled') {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });

  // Prefer the freshest payload: WS beats REST when both exist.
  const restJob = normalizeJob(restQuery.data);
  const liveJob = normalizeJob(liveRaw);
  const job = liveJob && restJob && liveRaw ? liveJob : restJob;

  const handleRetry = async () => {
    if (!job?.sourceId) {
      // No source to re-run: just refresh state and reconnect by re-render.
      setLiveRaw(null);
      restQuery.refetch();
      return;
    }
    try {
      const newJob = await jobsApi.triggerJob({
        source_id: job.sourceId,
        retry_of: job.id,
      });
      const newJobId = newJob?.job_id || newJob?.id || newJob?.jobId;
      if (newJobId && onJobChange) onJobChange(newJobId);
    } catch {
      setLiveRaw(null);
      restQuery.refetch();
    }
  };

  if (!jobId) {
    return (
      <div className="card p-4 text-sm text-slate-500">
        Upload a file to start an AI processing job and monitor it here.
      </div>
    );
  }

  const activeStep = job?.status === 'completed' ? PIPELINE_STEPS.length - 1 : job?.stepIndex ?? -1;
  const failed = job?.status === 'failed';
  const done = job?.status === 'completed';

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-800">
            Job {job?.id ? String(job.id).slice(0, 8) : ''}…
          </div>
          <div className="text-xs text-slate-500">
            {JOB_TYPE_LABELS[job?.type] || job?.type || 'Processing'} · WebSocket: {socketState}
          </div>
        </div>
        {job && (
          <span className={`badge ${JOB_STATUS_STYLES[job.status] || JOB_STATUS_STYLES.pending}`}>
            {job.status}
          </span>
        )}
      </div>

      {/* Overall progress */}
      <div className="mt-3">
        <div className="flex justify-between text-xs text-slate-500">
          <span>Overall progress</span>
          <span>{job ? `${job.percent}%` : '—'}</span>
        </div>
        <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full transition-all ${failed ? 'bg-red-500' : done ? 'bg-emerald-500' : 'bg-brand-600'}`}
            style={{ width: `${job?.percent || 0}%` }}
          />
        </div>
      </div>

      {/* Step indicator */}
      <ol className="mt-4 space-y-2">
        {PIPELINE_STEPS.map((step, idx) => {
          const state = failed && idx === Math.max(activeStep, 0)
            ? 'failed'
            : idx < activeStep || done
              ? 'done'
              : idx === activeStep
                ? 'active'
                : 'todo';
          return (
            <li key={step.key} className="flex items-center gap-3">
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                  state === 'done'
                    ? 'bg-emerald-500 text-white'
                    : state === 'active'
                      ? 'bg-brand-600 text-white'
                      : state === 'failed'
                        ? 'bg-red-500 text-white'
                        : 'bg-slate-200 text-slate-500'
                }`}
              >
                {state === 'done' ? '✓' : idx + 1}
              </span>
              <span
                className={`text-sm ${
                  state === 'active'
                    ? 'font-medium text-brand-700'
                    : state === 'todo'
                      ? 'text-slate-400'
                      : 'text-slate-700'
                }`}
              >
                {step.label}
              </span>
              {state === 'active' && !failed && (
                <span className="ml-auto text-xs text-slate-500">{job?.percent ?? 0}%</span>
              )}
            </li>
          );
        })}
      </ol>

      {/* Confidence + error */}
      {job?.confidence != null && (
        <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
          ML confidence score:{' '}
          <span className="font-semibold text-slate-800">
            {(job.confidence * 100).toFixed(1)}%
          </span>
        </div>
      )}
      {failed && (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2">
          <div className="text-xs font-medium text-red-700">Pipeline failed</div>
          <div className="mt-0.5 text-xs text-red-600">{job.error || 'Unknown error'}</div>
          <button type="button" className="btn-secondary mt-2" onClick={handleRetry}>
            Retry job
          </button>
        </div>
      )}
      {restQuery.isLoading && (
        <div className="mt-3 text-xs text-slate-500">Loading job status…</div>
      )}
      {!job && restQuery.isError && (
        <div className="mt-3 text-xs text-red-600">
          Could not load job status — is the backend running?
        </div>
      )}
    </div>
  );
}
