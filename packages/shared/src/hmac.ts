import { createHmac, timingSafeEqual } from 'node:crypto';

export const HMAC_HEADER = 'x-research-hub-signature';
export const HMAC_TIMESTAMP_HEADER = 'x-research-hub-timestamp';
export const HMAC_MAX_SKEW_SECONDS = 300;

export function signPayload(secret: string, timestamp: string, body: string): string {
  const mac = createHmac('sha256', secret);
  mac.update(`${timestamp}.${body}`);
  return `sha256=${mac.digest('hex')}`;
}

export function verifySignature(
  secret: string,
  timestamp: string,
  body: string,
  signature: string,
  nowSeconds: number = Math.floor(Date.now() / 1000),
): boolean {
  const ts = Number.parseInt(timestamp, 10);
  if (!Number.isFinite(ts) || Math.abs(nowSeconds - ts) > HMAC_MAX_SKEW_SECONDS) {
    return false;
  }
  const expected = signPayload(secret, timestamp, body);
  const a = Buffer.from(expected);
  const b = Buffer.from(signature);
  return a.length === b.length && timingSafeEqual(a, b);
}
