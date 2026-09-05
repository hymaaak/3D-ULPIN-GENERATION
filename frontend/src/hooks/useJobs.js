import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as jobsApi from '../api/jobs.js';
import { asList, normalizeStep, PIPELINE_STEPS } from '../utils/constants.js';

export function useJobs(params = {}) {
  const query = useQuery({
    queryKey: ['jobs', params],
    queryFn: () => jobsApi.listJobs({ limit: 50, ...params }),
  });
  return { ...query, jobs: asList(query.data) };
}

export function useJob(id, options = {}) {
  const query = useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.getJob(id),
    enabled: Boolean(id),
    refetchInterval: options.refetchInterval ?? false,
  });
  return { ...query, job: query.data };
}

// Live WebSocket feed for a single job. Falls back silently — callers also
// poll via useJob so a dead socket never stalls the UI.
export function useJobSocket(jobId, onMessage) {
  const [socketState, setSocketState] = useState('idle');
  const callbackRef = useRef(onMessage);
  callbackRef.current = onMessage;

  useEffect(() => {
    if (!jobId) return undefined;
    let closed = false;
    let ws;
    try {
      ws = new WebSocket(jobsApi.jobSocketUrl(jobId));
    } catch {
      setSocketState('error');
      return undefined;
    }
    setSocketState('connecting');

    ws.onopen = () => {
      if (!closed) setSocketState('open');
    };
    ws.onmessage = (event) => {
      try {
        callbackRef.current?.(JSON.parse(event.data));
      } catch {
        callbackRef.current?.({ raw: event.data });
      }
    };
    ws.onerror = () => {
      if (!closed) setSocketState('error');
    };
    ws.onclose = () => {
      if (!closed) setSocketState('closed');
    };

    return () => {
      closed = true;
      ws.close();
      setSocketState('idle');
    };
  }, [jobId]);

  return socketState;
}

// Normalize heterogeneous job payloads (REST + WS) into a shape the
// JobMonitor stepper understands.
export function normalizeJob(raw) {
  if (!raw) return null;
  const stepKey = normalizeStep(raw.current_step || raw.step || raw.stage);
  const stepIndex = stepKey ? PIPELINE_STEPS.findIndex((s) => s.key === stepKey) : -1;
  const status = String(raw.status || 'pending').toLowerCase();
  const percent =
    typeof raw.progress === 'number'
      ? raw.progress
      : typeof raw.percent === 'number'
        ? raw.percent
        : status === 'completed'
          ? 100
          : status === 'failed'
            ? 100
            : stepIndex >= 0
              ? Math.round(((stepIndex + 1) / PIPELINE_STEPS.length) * 100)
              : 0;
  return {
    id: raw.job_id || raw.id || raw.jobId,
    type: raw.job_type || raw.type,
    status,
    stepKey,
    stepIndex,
    percent: Math.min(100, Math.max(0, percent)),
    confidence: raw.confidence_score ?? raw.confidence ?? null,
    error: raw.error_message || raw.error || null,
    sourceId: raw.source_id || raw.sourceId || null,
    parcelId: raw.parcel_id || raw.parcelId || null,
    createdAt: raw.created_at || raw.createdAt || null,
    completedAt: raw.completed_at || raw.completedAt || null,
    result: raw.result_metadata || raw.result || null,
    raw,
  };
}

export function useInvalidateJobs() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    queryClient.invalidateQueries({ queryKey: ['job'] });
  };
}
