import type { components } from './types';
import createdExample from '../../../contracts/examples/CheckCreated.json';
import completedExample from '../../../contracts/examples/check_result.json';
import sourceExample from '../../../contracts/examples/SourcePublic.json';
import errorExample from '../../../contracts/examples/error.json';
import scenarios from './scenarios.json';
import { errorMessages } from './presentation';
export type Schema = components['schemas'];
export type CheckCreate = Schema['CheckCreate'];
export type CheckRecord = Schema['CheckRecord'];
export type SourcePublic = Schema['SourcePublic'];
export type Scenario = keyof typeof scenarios | 'request_error';
export interface ApiClient {
  createCheck(input: CheckCreate): Promise<Schema['CheckCreated']>;
  getCheck(checkId: string, token: string): Promise<CheckRecord>;
  getSource(versionId: string): Promise<SourcePublic>;
}
export class ApiError extends Error {
  constructor(public detail: Schema['ErrorDetail']) { super(detail.message); }
}
const copy = <T,>(data: unknown): T => structuredClone(data) as T;
// Deliberately fixed fixture responses. Input is never sent, persisted or evaluated.
export function createMockClient(scenario: Scenario): ApiClient {
  let polls = 0;
  return {
    async createCheck(_input) {
      polls = 0;
      if (scenario === 'request_error') throw new ApiError(copy<Schema['ErrorDetail']>(errorExample.error));
      return copy(createdExample);
    },
    async getCheck(checkId, token) {
      if (checkId !== createdExample.check.check_id || token !== createdExample.access_token) {
        throw new ApiError({ code: 'RESOURCE_NOT_FOUND', message: 'Không tìm thấy phiên kiểm tra.', retryable: false, details: {} });
      }
      const status = (['extracting', 'retrieving', 'verifying'] as const)[polls++];
      if (status) return { ...copy<CheckRecord>(createdExample.check), status };
      return copy(scenario === 'original' ? completedExample : scenarios[scenario === 'request_error' ? 'mixed' : scenario]);
    },
    async getSource(versionId) {
      if (versionId !== sourceExample.version_id) throw new ApiError({ code: 'RESOURCE_NOT_FOUND', message: 'Không tìm thấy snapshot.', retryable: false, details: {} });
      return copy(sourceExample);
    },
  };
}
export const POLL_MS = 1500;
export const POLL_LIMIT_MS = 120000;
export async function pollCheck(client: ApiClient, checkId: string, token: string, onRecord: (record: CheckRecord) => void) {
  const start = Date.now();
  while (Date.now() - start < POLL_LIMIT_MS) {
    await new Promise(resolve => setTimeout(resolve, POLL_MS));
    const record = await client.getCheck(checkId, token);
    onRecord(record);
    if (record.status === 'completed' || record.status === 'failed') return 'finished' as const;
  }
  return 'slow' as const;
}

// The normal app always uses HTTP. Mock mode is explicit and never an error fallback.
export function createHttpClient(): ApiClient {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`/api/v1${path}`, { ...init, signal: AbortSignal.timeout(10000), cache: 'no-store' });
    } catch {
      throw new ApiError({ code: 'INTERNAL_ERROR', message: 'Không kết nối được FastAPI. Kiểm tra backend rồi thử lại.', retryable: true, details: {} });
    }
    let body: unknown;
    try { body = await response.json(); }
    catch { throw new ApiError({code:'INTERNAL_ERROR',message:'Backend trả phản hồi không hợp lệ.',retryable:true,details:{}}); }
    if (!response.ok) {
      const envelope = body as Schema['ErrorEnvelope'];
      if (envelope?.schema_version === '1.0' && envelope.error && typeof envelope.error.message === 'string' && envelope.error.code in errorMessages) {
        throw new ApiError(envelope.error);
      }
      throw new ApiError({code:'INTERNAL_ERROR',message:`Backend trả HTTP ${response.status}.`,retryable:true,details:{}});
    }
    if (!body || typeof body !== 'object' || !('schema_version' in body) || body.schema_version !== '1.0') {
      throw new ApiError({code:'INTERNAL_ERROR',message:'Backend trả schema không hợp lệ.',retryable:false,details:{}});
    }
    return body as T;
  }
  function invalid(): never { throw new ApiError({code:'INTERNAL_ERROR',message:'Backend trả dữ liệu không hợp lệ.',retryable:false,details:{}}); }
  function validRecord(record: CheckRecord): boolean {
    return !!record && typeof record.check_id === 'string' &&
      ['queued','extracting','retrieving','verifying','completed','failed'].includes(record.status) &&
      (record.status === 'completed' ? record.error === null && record.result?.schema_version === '1.0' &&
        record.result.check_id === record.check_id && record.result.run_mode === 'fixture' &&
        Array.isArray(record.result.claims) && record.result.claims.every(c=>['supported','contradicted','insufficient_evidence'].includes(c.label))
      : record.status === 'failed' ? record.result === null && !!record.error && record.error.code in errorMessages
      : record.result === null && record.error === null);
  }
  return {
    async createCheck(input) {
      const created = await request<Schema['CheckCreated']>('/checks', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(input) });
      if (!validRecord(created.check) || created.check.status !== 'queued' || typeof created.access_token !== 'string' || !created.access_token) invalid();
      return created;
    },
    async getCheck(checkId, token) {
      const record = await request<CheckRecord>(`/checks/${encodeURIComponent(checkId)}`, { headers:{'X-Resource-Token':token} });
      if (!validRecord(record) || record.check_id !== checkId) invalid();
      return record;
    },
    async getSource(versionId) {
      const source = await request<SourcePublic>(`/sources/${encodeURIComponent(versionId)}`);
      if (source.version_id !== versionId || !source.is_fixture || typeof source.text !== 'string' || !Array.isArray(source.chunks)) invalid();
      return source;
    },
  };
}
