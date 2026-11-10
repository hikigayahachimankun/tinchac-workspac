import { afterEach, expect, it, vi } from 'vitest';
import { ApiError, createHttpAssetClient } from '../src/api/client';
import example from '../../contracts/examples/AssetCreated.json';
afterEach(()=>vi.unstubAllGlobals());
it('uploads multipart and uses memory capabilities only in resource headers',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(example)))
  .mockResolvedValueOnce(new Response(JSON.stringify(example.asset)))
  .mockResolvedValueOnce(new Response(null,{status:204}));
 vi.stubGlobal('fetch',fetch);
 const client=createHttpAssetClient();
 const file=new File(['image'],'notice.png',{type:'image/png'});
 const created=await client.createAsset(file);
 await client.getAsset(created.asset.asset_id,created.access_token);
 await client.deleteAsset(created.asset.asset_id,created.access_token);
 const [url,init]=fetch.mock.calls[0]!;
 expect(url).toBe('/api/v1/assets');expect(init.body).toBeInstanceOf(FormData);
 expect((init.body as FormData).get('file')).toBe(file);
 expect(init.headers).toBeUndefined();
 for(const [resource,options] of fetch.mock.calls.slice(1)) {
  expect(resource).not.toContain(created.access_token);
  expect(options.headers).toEqual({'X-Resource-Token':created.access_token});
 }
});
it('keeps expired assets and failed requests as technical errors',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({schema_version:'1.0',request_id:'fixture',error:{code:'RESOURCE_EXPIRED',message:'Hết hạn',retryable:false,details:{}}}),{status:410})));
 await expect(createHttpAssetClient().getAsset('id','secret')).rejects.toBeInstanceOf(ApiError);
});
