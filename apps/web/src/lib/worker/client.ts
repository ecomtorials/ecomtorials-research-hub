import { signPayload, HMAC_HEADER, HMAC_TIMESTAMP_HEADER } from '@research-hub/shared';
import type { JobPayload } from '@research-hub/shared';

function workerConfig() {
  const url = process.env.RESEARCH_WORKER_URL;
  const secret = process.env.RESEARCH_WORKER_SECRET;
  if (!url || !secret) {
    throw new Error('RESEARCH_WORKER_URL or RESEARCH_WORKER_SECRET not set');
  }
  return { url, secret };
}

export async function triggerWorker(payload: JobPayload): Promise<void> {
  const { url, secret } = workerConfig();
  const body = JSON.stringify(payload);
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = signPayload(secret, timestamp, body);

  const res = await fetch(`${url}/jobs`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      [HMAC_HEADER]: signature,
      [HMAC_TIMESTAMP_HEADER]: timestamp,
    },
    body,
    // Worker takes a long time to confirm accept; don't wait on response pipeline.
    // Keep a short timeout: worker should 202 Accepted within seconds.
    signal: AbortSignal.timeout(15000),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Worker rejected job (${res.status}): ${text.slice(0, 200)}`);
  }
}

/**
 * Tell the worker to cooperatively cancel a running job. Best-effort: the DB
 * status is flipped to 'cancelled' independently, so a worker outage doesn't
 * leave the UI stuck. Short timeout — if the worker is unreachable we swallow.
 */
export async function cancelWorkerJob(jobId: string): Promise<void> {
  const { url, secret } = workerConfig();
  const body = '';
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = signPayload(secret, timestamp, body);

  const res = await fetch(`${url}/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      [HMAC_HEADER]: signature,
      [HMAC_TIMESTAMP_HEADER]: timestamp,
    },
    body,
    signal: AbortSignal.timeout(5000),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Worker cancel rejected (${res.status}): ${text.slice(0, 200)}`);
  }
}
