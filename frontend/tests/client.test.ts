import { it, expect, vi } from 'vitest';
import { createMockClient, ApiError, pollCheck } from '../src/api/client';
import input from '../../contracts/examples/check_create.json';
import type { CheckCreate, CheckRecord, ApiClient } from '../src/api/client';
it('returns queued then contract stages and a completed mixed fixture',async()=>{
 const client=createMockClient('mixed');const response=await client.createCheck(input as CheckCreate);
 expect(response.check.status).toBe('queued');
 for(const status of ['extracting','retrieving','verifying','completed']) expect((await client.getCheck(response.check.check_id,response.access_token)).status).toBe(status);
 const result=await client.getCheck(response.check.check_id,response.access_token);
 expect(result.result!.claims.map(c=>c.label)).toEqual(['supported','contradicted','insufficient_evidence']);
 await expect(client.getCheck(response.check.check_id,'wrong-token')).rejects.toBeInstanceOf(ApiError);
});
it('keeps create errors and worker errors distinct from completed NEI',async()=>{
 await expect(createMockClient('request_error').createCheck(input as CheckCreate)).rejects.toBeInstanceOf(ApiError);
 const client=createMockClient('failed');const response=await client.createCheck(input as CheckCreate);
 let last:CheckRecord=response.check;for(let i=0;i<4;i++) last=await client.getCheck(response.check.check_id,response.access_token);
 expect(last.status).toBe('failed');expect(last.result).toBeNull();expect(last.error!.code).toBe('PROVIDER_TIMEOUT');
});
it('stops polling after 120 seconds without creating another check',async()=>{
 vi.useFakeTimers();
 try {
  const progress={status:'retrieving'} as CheckRecord;
  const client={getCheck:vi.fn().mockResolvedValue(progress),createCheck:vi.fn(),getSource:vi.fn()} as ApiClient;
  const pending=pollCheck(client,'fixture-id','memory-token',()=>{});
  await vi.advanceTimersByTimeAsync(120000);
  expect(await pending).toBe('slow');expect(client.createCheck).not.toHaveBeenCalled();
  expect(client.getCheck).toHaveBeenCalledTimes(80);
 } finally { vi.useRealTimers(); }
});
