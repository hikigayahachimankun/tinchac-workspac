import type { components } from './types';
import createdExample from '../../../contracts/examples/CheckCreated.json';
import completedExample from '../../../contracts/examples/check_result.json';
import sourceExample from '../../../contracts/examples/SourcePublic.json';
import errorExample from '../../../contracts/examples/error.json';
import scenarios from './scenarios.json';
import { errorMessages, labels, temporal } from './presentation';
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
export async function pollCheck(client: ApiClient, checkId: string, token: string, onRecord: (record: CheckRecord) => void, signal?: AbortSignal) {
  const start = Date.now();
  while (Date.now() - start < POLL_LIMIT_MS) {
    if(signal?.aborted) return 'canceled' as const;
    await new Promise<void>(resolve => {
      const finish=()=>{clearTimeout(timer);signal?.removeEventListener('abort',finish);resolve();};
      const timer=setTimeout(finish,POLL_MS);
      signal?.addEventListener('abort',finish,{once:true});
    });
    if(signal?.aborted) return 'canceled' as const;
    const record = await client.getCheck(checkId, token);
    if(signal?.aborted) return 'canceled' as const;
    onRecord(record);
    if (record.status === 'completed' || record.status === 'failed') return 'finished' as const;
  }
  return 'slow' as const;
}

// Validate fields consumed by the UI before putting untrusted HTTP JSON in React state.
// Pydantic remains the contract authority; the client does not infer or repair verdicts.
const stringList = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === 'string');
const validDate = (value: unknown) => typeof value === 'string' && Number.isFinite(Date.parse(value));
function validError(error: Schema['ErrorDetail'] | null | undefined): boolean {
  return !!error && typeof error.code === 'string' && Object.hasOwn(errorMessages, error.code) &&
    typeof error.message === 'string' && typeof error.retryable === 'boolean';
}
function invalid(): never {
  throw new ApiError({code:'INTERNAL_ERROR',message:'Backend trả dữ liệu không hợp lệ.',retryable:false,details:{}});
}
function validSource(source: Schema['SourceSummary']): boolean {
  return !!source && typeof source.version_id === 'string' && typeof source.title === 'string' &&
    typeof source.canonical_url === 'string' && typeof source.is_fixture === 'boolean' &&
    (source.published_at === null || validDate(source.published_at)) && validDate(source.retrieved_at);
}
function validResult(result: Schema['CheckResult'], checkId: string): boolean {
  if (!result || result.schema_version !== '1.0' || result.check_id !== checkId ||
      !['fixture','replay','live'].includes(result.run_mode) || !validDate(result.as_of) ||
      !validDate(result.corpus_updated_at) || typeof result.corpus_version !== 'string' ||
      !stringList(result.warnings) || !stringList(result.next_steps) || !result.summary ||
      typeof result.summary.message !== 'string' || !Array.isArray(result.sources) ||
      !result.sources.every(validSource) || !Array.isArray(result.claims)) return false;
  const versions = new Set(result.sources.map(source => source.version_id));
  if (versions.size !== result.sources.length || !result.claims.every(claim =>
      !!claim && typeof claim.claim_id === 'string' && typeof claim.statement === 'string' &&
      typeof claim.explanation === 'string' && typeof claim.label === 'string' && Object.hasOwn(labels, claim.label) &&
      typeof claim.temporal_status === 'string' && Object.hasOwn(temporal, claim.temporal_status) &&
      Array.isArray(claim.evidence) && claim.evidence.every(ref => !!ref &&
        typeof ref.version_id === 'string' && versions.has(ref.version_id) && typeof ref.chunk_id === 'string' &&
        typeof ref.quote === 'string' && ['supports','contradicts','context'].includes(ref.relation)) &&
      (claim.label === 'insufficient_evidence' || claim.evidence.some(ref =>
        ref.relation === (claim.label === 'supported' ? 'supports' : 'contradicts'))))) return false;
  return new Set(result.claims.map(claim => claim.claim_id)).size === result.claims.length &&
    (Object.keys(labels) as Schema['Label'][]).every(label => Number.isSafeInteger(result.summary[label]) &&
      result.summary[label] === result.claims.filter(claim => claim.label === label).length);
}

// The normal app always uses HTTP. Mock mode is explicit and never an error fallback.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`/api/v1${path}`, { ...init, signal: AbortSignal.timeout(10000), cache: 'no-store' });
    } catch {
      throw new ApiError({ code: 'INTERNAL_ERROR', message: 'Không kết nối được FastAPI. Kiểm tra backend rồi thử lại.', retryable: true, details: {} });
    }
    if (response.status === 204 && response.ok) return undefined as T;
    let body: unknown;
    try { body = await response.json(); }
    catch { throw new ApiError({code:'INTERNAL_ERROR',message:'Backend trả phản hồi không hợp lệ.',retryable:true,details:{}}); }
    if (!response.ok) {
      const envelope = body as Schema['ErrorEnvelope'];
      if (envelope?.schema_version === '1.0' && validError(envelope.error)) {
        throw new ApiError(envelope.error);
      }
      throw new ApiError({code:'INTERNAL_ERROR',message:`Backend trả HTTP ${response.status}.`,retryable:true,details:{}});
    }
    if (!body || typeof body !== 'object' || !('schema_version' in body) || body.schema_version !== '1.0') {
      throw new ApiError({code:'INTERNAL_ERROR',message:'Backend trả schema không hợp lệ.',retryable:false,details:{}});
    }
    return body as T;
  }
export function createHttpClient(): ApiClient {
  function validRecord(record: CheckRecord): boolean {
    return !!record && typeof record.check_id === 'string' &&
      ['queued','extracting','retrieving','verifying','completed','failed'].includes(record.status) &&
      (record.status === 'completed' ? record.error === null && !!record.result && validResult(record.result, record.check_id)
      : record.status === 'failed' ? record.result === null && validError(record.error)
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
      if (!validSource(source) || source.version_id !== versionId || typeof source.text !== 'string' || !Array.isArray(source.chunks)) invalid();
      return source;
    },
  };
}

export interface AssetClient {
  createAsset(file: File): Promise<Schema['AssetCreated']>;
  getAsset(id: string, token: string): Promise<Schema['AssetRecord']>;
  deleteAsset(id: string, token: string): Promise<void>;
}
export function createHttpAssetClient(): AssetClient {
  return {
    createAsset(file) {
      const body = new FormData(); body.append('file', file);
      return request('/assets', {method:'POST', body});
    },
    getAsset(id, token) { return request(`/assets/${encodeURIComponent(id)}`, {headers:{'X-Resource-Token':token}}); },
    deleteAsset(id, token) { return request(`/assets/${encodeURIComponent(id)}`, {method:'DELETE',headers:{'X-Resource-Token':token}}); },
  };
}

// Health is read-only; never infer live/fixture from an error or provider presence.
export async function getRunMode(): Promise<Schema['RunMode']> {
  const health=await request<Schema['HealthResponse']>('/health');
  if(!['fixture','replay','live'].includes(health.run_mode)) throw new ApiError({code:'INTERNAL_ERROR',message:'Chế độ backend không hợp lệ.',retryable:true,details:{}});
  return health.run_mode;
}

export function deleteCheck(checkId:string, token:string): Promise<void> {
  return request(`/checks/${encodeURIComponent(checkId)}`, {method:'DELETE',headers:{'X-Resource-Token':token}});
}
