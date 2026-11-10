import { afterEach, expect, it, vi } from 'vitest';
import { ApiError, createHttpAssetClient, createHttpClient, deleteCheck } from '../src/api/client';
import example from '../../contracts/examples/check_result.json';
import created from '../../contracts/examples/CheckCreated.json';
import request from '../../contracts/examples/check_create.json';

const canary = 'SYNTHETIC_PRIVATE_T12';
afterEach(() => vi.unstubAllGlobals());

it('keeps check text in POST body and capabilities in headers, with no logging', async () => {
  const info = vi.spyOn(console, 'info').mockImplementation(() => {});
  const log = vi.spyOn(console, 'log').mockImplementation(() => {});
  const error = vi.spyOn(console, 'error').mockImplementation(() => {});
  try {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json(created))
      .mockResolvedValueOnce(Response.json(example))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(Response.json({ schema_version: '1.0', status: 'ready' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetcher);
    const client = createHttpClient();
    await client.createCheck({ ...request, schema_version: '1.0', input_mode: 'text', confirmed_text: canary, consent_to_process: true });
    await client.getCheck(example.check_id, canary);
    await deleteCheck(example.check_id, canary);
    await createHttpAssetClient().getAsset('synthetic-id', canary);
    await createHttpAssetClient().deleteAsset('synthetic-id', canary);
    expect(fetcher.mock.calls.every(([url]) => !String(url).includes(canary))).toBe(true);
    expect(JSON.parse(fetcher.mock.calls[0]![1].body).confirmed_text).toBe(canary);
    for (const [, init] of fetcher.mock.calls.slice(1)) {
      expect(init.headers['X-Resource-Token']).toBe(canary);
      expect(init.body).toBeUndefined();
    }
    expect(log).not.toHaveBeenCalled(); expect(info).not.toHaveBeenCalled(); expect(error).not.toHaveBeenCalled();
  } finally { vi.restoreAllMocks(); }
});

it.each([['html', () => new Response('<html>proxy error</html>', { status: 502 })],
         ['wrong schema', () => Response.json({ schema_version: '2.0' })],
         ['network', () => Promise.reject(new Error(canary))]] as const)(
  'treats %s response as technical error without echoing transport internals', async (_name, response) => {
    vi.stubGlobal('fetch', vi.fn(response));
    await expect(createHttpClient().getCheck(example.check_id, canary)).rejects.toMatchObject({
      detail: { code: 'INTERNAL_ERROR' },
    });
    try { await createHttpClient().getCheck(example.check_id, canary); }
    catch (problem) { expect(problem).toBeInstanceOf(ApiError); expect(String(problem)).not.toContain(canary); }
  });

// T12-B01 regression: malformed successful responses must never reach React.
it.each([
  ['missing summary', { ...example.result, summary: null }],
  ['missing warnings', { ...example.result, warnings: null }],
  ['invalid timestamp', { ...example.result, as_of: 'invalid-date' }],
  ['missing sources', { ...example.result, sources: null }],
  ['null claim', { ...example.result, claims: [null] }],
  ['object statement', { ...example.result, claims: example.result.claims.map(claim => ({ ...claim, statement: {} })) }],
  ['missing evidence', { ...example.result, claims: example.result.claims.map(claim => ({ ...claim, evidence: null })) }],
  ['invalid source timestamp', { ...example.result, sources: example.result.sources.map(source => ({ ...source, retrieved_at: 'invalid-date' })) }],
  ['summary mismatch', { ...example.result, summary: { ...example.result.summary, supported: 999 } }],
  ['lost cited source', { ...example.result, sources: [] }],
  ['unsupported citation relation', { ...example.result, claims: example.result.claims.map(claim => ({ ...claim, evidence: claim.evidence.map(ref => ({ ...ref, relation: 'context' })) })) }],
])('T12-B01: rejects completed result with %s before React renders it', async (_name, result) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ ...example, result })));
  await expect(createHttpClient().getCheck(example.check_id, canary)).rejects.toBeInstanceOf(ApiError);
});


it('rejects malformed public snapshot metadata before it reaches the evidence panel', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({
    schema_version: '1.0', version_id: 'bad', is_fixture: false, text: 'snapshot', chunks: [],
    title: 'Source', canonical_url: 'https://dut.udn.vn/', published_at: null, retrieved_at: 'invalid-date',
  })));
  await expect(createHttpClient().getSource('bad')).rejects.toBeInstanceOf(ApiError);
});

it('rejects inherited names in error codes rather than rendering an invalid error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({
    schema_version: '1.0', error: { code: 'toString', message: 'Invalid error', retryable: true },
  }, { status: 500 })));
  await expect(createHttpClient().getCheck(example.check_id, canary)).rejects.toMatchObject({ detail: { code: 'INTERNAL_ERROR' } });
});
