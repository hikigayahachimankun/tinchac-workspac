import { afterEach, expect, it, vi } from 'vitest';
import { ApiError, createHttpClient } from '../src/api/client';
import input from '../../contracts/examples/check_create.json';
import created from '../../contracts/examples/CheckCreated.json';
import completed from '../../contracts/examples/check_result.json';
import type { CheckCreate } from '../src/api/client';

afterEach(()=>vi.unstubAllGlobals());
it('sends create JSON and resource token only in the header',async()=>{
 const fetcher=vi.fn().mockResolvedValueOnce(Response.json(created)).mockResolvedValueOnce(Response.json(completed));
 vi.stubGlobal('fetch',fetcher);
 const client=createHttpClient();
 const response=await client.createCheck(input as CheckCreate);
 await client.getCheck(response.check.check_id,response.access_token);
 expect(fetcher.mock.calls[0]![0]).toBe('/api/v1/checks');
 expect(fetcher.mock.calls[0]![1].method).toBe('POST');
 expect(JSON.parse(fetcher.mock.calls[0]![1].body)).toEqual(input);
 const [url,options]=fetcher.mock.calls[1]!;
 expect(url).toBe(`/api/v1/checks/${response.check.check_id}`);
 expect(url).not.toContain(response.access_token);
 expect(options.headers).toEqual({'X-Resource-Token':response.access_token});
});
it('does not return a mock after backend, transport, or malformed response errors',async()=>{
 const client=createHttpClient();
 const fetcher=vi.fn().mockResolvedValueOnce(Response.json({schema_version:'1.0',request_id:'test',error:{code:'RESOURCE_EXPIRED',message:'Expired',retryable:false,details:{}}},{status:410}))
  .mockRejectedValueOnce(new TypeError('offline'))
  .mockResolvedValueOnce(Response.json({schema_version:'1.0',check:{status:'queued'}}));
 vi.stubGlobal('fetch',fetcher);
 await expect(client.getCheck('id','token')).rejects.toMatchObject({detail:{code:'RESOURCE_EXPIRED'}});
 await expect(client.createCheck(input as CheckCreate)).rejects.toBeInstanceOf(ApiError);
 await expect(client.createCheck(input as CheckCreate)).rejects.toBeInstanceOf(ApiError);
 expect(fetcher).toHaveBeenCalledTimes(3);
});
it('keeps a backend worker error as failed rather than NEI',async()=>{
 const failed={...completed,status:'failed',result:null,error:{code:'PROVIDER_TIMEOUT',message:'Worker failed',retryable:true,details:{}}};
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json(failed)));
 const result=await createHttpClient().getCheck(completed.check_id,'memory-token');
 expect(result.status).toBe('failed');expect(result.result).toBeNull();
});
