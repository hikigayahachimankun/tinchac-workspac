import { afterEach, expect, it, vi } from 'vitest';
import { createHttpClient, deleteCheck, getRunMode, pollCheck } from '../src/api/client';
import completed from '../../contracts/examples/check_result.json';
import source from '../../contracts/examples/SourcePublic.json';
import type { CheckRecord } from '../src/api/client';
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
it('accepts fixture/replay/live records and public snapshots without fixture fallback',async()=>{
 for(const run_mode of ['fixture','replay','live']) {
  const fetcher=vi.fn().mockResolvedValueOnce(Response.json({...completed,result:{...completed.result,run_mode}}))
   .mockResolvedValueOnce(Response.json({...source,is_fixture:false}));vi.stubGlobal('fetch',fetcher);
  const client=createHttpClient();
  expect((await client.getCheck(completed.check_id,'private')).result!.run_mode).toBe(run_mode);
  expect((await client.getSource(source.version_id)).is_fixture).toBe(false);
 }
});
it('health is read only and DELETE carries token in header, never URL',async()=>{
 const fetcher=vi.fn().mockResolvedValueOnce(Response.json({schema_version:'1.0',run_mode:'live'})).mockResolvedValueOnce(new Response(null,{status:204}));
 vi.stubGlobal('fetch',fetcher);
 expect(await getRunMode()).toBe('live');await deleteCheck('id','private-token');
 expect(fetcher.mock.calls[0]![0]).toBe('/api/v1/health');
 expect(fetcher.mock.calls[1]![0]).toBe('/api/v1/checks/id');
 expect(fetcher.mock.calls[1]![1]).toMatchObject({method:'DELETE',headers:{'X-Resource-Token':'private-token'}});
});
it('cancel stops polling before another GET and suppresses in-flight results',async()=>{
 vi.useFakeTimers();const controller=new AbortController();const onRecord=vi.fn();
 let finish!:(r:CheckRecord)=>void;
 const client={getCheck:vi.fn(()=>new Promise<CheckRecord>(resolve=>{finish=resolve;})),getSource:vi.fn(),createCheck:vi.fn()};
 const pending=pollCheck(client,'id','token',onRecord,controller.signal);
 await vi.advanceTimersByTimeAsync(1500);controller.abort();finish(completed as CheckRecord);
 expect(await pending).toBe('canceled');expect(onRecord).not.toHaveBeenCalled();
 const next=new AbortController();const stopped=pollCheck(client,'id','token',onRecord,next.signal);next.abort();
 expect(await stopped).toBe('canceled');expect(client.getCheck).toHaveBeenCalledTimes(1);
 expect(client.createCheck).not.toHaveBeenCalled();
});
