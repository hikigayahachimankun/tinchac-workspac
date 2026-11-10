import { useMemo, useRef, useState, useEffect } from 'react';
import { ApiError, createHttpClient, createHttpAssetClient, createMockClient, deleteCheck, getRunMode, pollCheck } from './api/client';
import type { CheckRecord, Scenario, Schema } from './api/client';
import requestExample from '../../contracts/examples/check_create.json';
import { errorMessages, recordView } from './api/presentation';
import { OCRReview } from './components/OCRReview';
import type { ImageConfirmation } from './components/OCRReview';
import { InputForm } from './components/InputForm';
import { ProgressPanel } from './components/ProgressPanel';
import { ResultTable, modeNames } from './components/ResultTable';
export default function App() {
 const assetClient=useMemo(()=>createHttpAssetClient(),[]);
 const [mode,setMode]=useState<'text'|'image'>('text');
 const [scenario,setScenario]=useState<Scenario>('mixed');
 const mockMode=import.meta.env.VITE_API_MODE==='mock';
 const client=useMemo(()=>mockMode?createMockClient(scenario):createHttpClient(),[scenario,mockMode]);
 const [runMode,setRunMode]=useState<Schema['RunMode']|null>(mockMode?'fixture':null);
 const [healthError,setHealthError]=useState(false);
 const [record,setRecord]=useState<CheckRecord|null>(null);
 const [busy,setBusy]=useState(false);
 const [slow,setSlow]=useState(false);
 const [error,setError]=useState<Schema['ErrorDetail']|null>(null);
 const [notice,setNotice]=useState('');
 const session=useRef<{id:string;token:string}|null>(null);
 const output=useRef<HTMLDivElement>(null);
 const retry=useRef<{text:string;asset?:ImageConfirmation}>({text:''});
 const generation=useRef(0);
 const polling=useRef<AbortController|null>(null);
 const locked=useRef(false);
 const submitting=useRef(false);
 async function readMode() {
  setHealthError(false);
  try {setRunMode(await getRunMode());}catch {setHealthError(true);}
 }
 useEffect(()=>{if(!mockMode) void readMode();},[mockMode]);
 useEffect(()=>()=>{generation.current++;polling.current?.abort();},[]);
 useEffect(()=>{if(error||record?.status==='completed'||record?.status==='failed'||slow||notice) output.current?.focus();},[error,record?.status,slow,notice]);
 function fail(problem:unknown) {setError(problem instanceof ApiError?problem.detail:{code:'INTERNAL_ERROR',message:'Có lỗi kỹ thuật.',retryable:true,details:{}});}
 async function removeSession() {
  const current=session.current;
  if(!current) return;
  try {if(!mockMode) await deleteCheck(current.id,current.token);}
  catch(problem) {
   if(!(problem instanceof ApiError)||!['RESOURCE_NOT_FOUND','RESOURCE_EXPIRED'].includes(problem.detail.code)) throw problem;
  }
  if(session.current===current) session.current=null;
 }
 async function monitor(version:number) {
  const current=session.current;if(!current) return;
  const controller=new AbortController();polling.current=controller;
  const status=await pollCheck(client,current.id,current.token,next=>{
   if(generation.current===version) {setRecord(next);if(next.result) setRunMode(next.result.run_mode);}
  },controller.signal);
  if(generation.current===version) setSlow(status==='slow');
 }
 async function submit(text:string,asset?:ImageConfirmation) {
  if(locked.current||!runMode) return;
  locked.current=true;submitting.current=true;const version=++generation.current;
  retry.current={text,asset};setError(null);setNotice('');setSlow(false);setBusy(true);
  try {
   await removeSession();
   if(generation.current!==version) return;
   setRecord(null);
   const response=await client.createCheck({...requestExample,schema_version:'1.0',input_mode:asset?'image':'text',confirmed_text:text,asset_id:asset?.asset_id??null,asset_token:asset?.asset_token??null,as_of:runMode==='fixture'?requestExample.as_of:new Date().toISOString(),consent_to_process:true});
   const created={id:response.check.check_id,token:response.access_token};
   if(generation.current!==version) {
    // A canceled POST can still create a job. Keep its capability until DELETE succeeds.
    session.current=created;
    try {await removeSession();}catch(problem){fail(problem);setNotice('Đã ngừng theo dõi nhưng chưa xóa được phiên đến muộn. Hãy thử hủy lại.');}
    return;
   }
   session.current=created;setRecord(response.check);await monitor(version);
  }catch(problem){if(generation.current===version) fail(problem);}
  finally{submitting.current=false;locked.current=false;setBusy(false);}
 }
 async function cancel() {
  ++generation.current;polling.current?.abort();locked.current=true;setBusy(true);setSlow(false);setError(null);setRecord(null);
  try {await removeSession();setNotice('Đã hủy theo dõi phiên. Phần xử lý đã gửi có thể đã phát sinh chi phí; hủy không bảo đảm hoàn phí.');}
  catch(problem){fail(problem);setNotice('Đã ngừng theo dõi; chưa xác nhận xóa dữ liệu trên máy chủ. Hãy thử hủy lại.');}
  finally{locked.current=submitting.current;setBusy(submitting.current);}
 }
 function changeMode(value:'text'|'image') {
  if(value===mode) return;
  ++generation.current;polling.current?.abort();
  void removeSession().catch(problem=>{fail(problem);setNotice('Chưa xóa được phiên cũ. Dùng nút hủy để thử lại.');});
  setMode(value);setRecord(null);setError(null);setSlow(false);setNotice('');retry.current={text:''};
 }
 async function resume() {
  if(locked.current||!session.current) return;
  locked.current=true;const version=++generation.current;setError(null);setSlow(false);setBusy(true);
  try {await monitor(version);}catch(problem){if(generation.current===version) fail(problem);}
  finally{if(generation.current===version){locked.current=false;setBusy(false);}}
 }
 const activeError=error??(record?.status==='failed'?record.error:null);
 const canResume=!!session.current&&record?.status!=='failed'&&record?.status!=='completed';
 const blocked=busy||slow||!runMode;
 return <><a className="skip-link" href="#main">Đến nội dung chính</a><header className="site-header"><a href="#main" className="wordmark">TinChắc<span className="brand-dot" aria-hidden="true">.</span></a><span>Đối chiếu thông báo học vụ</span></header>
  <div className="fixture-banner" role="note"><strong>{runMode==='fixture'?'Chế độ mô phỏng':runMode?modeNames[runMode]:'Chưa xác định chế độ backend'}</strong><span>{runMode==='fixture'?'Fixture · Dữ liệu và kết quả mẫu. Không dùng để quyết định nộp hồ sơ hoặc chuyển tiền.':runMode==='replay'?'Kết quả đã lưu từ trước; không phải lần gọi model mới.':runMode==='live'?'Đối chiếu bằng kho snapshot đã lưu; không xác nhận người gửi hoặc an toàn giao dịch.':healthError?'Không đọc được chế độ backend; chưa gửi nội dung.':'Đang đọc trạng thái hệ thống; chưa gửi nội dung.'}</span>{healthError&&<button onClick={()=>void readMode()}>Thử đọc lại chế độ</button>}</div>
  <main id="main"><div className="input-modes" aria-label="Loại đầu vào"><button aria-pressed={mode==='text'} disabled={busy||slow} onClick={()=>changeMode('text')}>Văn bản</button><button aria-pressed={mode==='image'} disabled={busy||slow||mockMode} onClick={()=>changeMode('image')}>Ảnh</button></div>
  {mode==='image'?<OCRReview client={assetClient} busy={blocked} onConfirm={submit}/>:<InputForm busy={blocked} mockMode={mockMode} runMode={runMode} scenario={scenario} onScenario={value=>{setScenario(value);setRecord(null);setError(null);setNotice('');void removeSession().catch(fail);}} onSubmit={submit}/>}
   <div ref={output} role="region" tabIndex={-1} className="output" aria-label="Trạng thái đối chiếu">
    {notice&&<p role="status">{notice}</p>}
    {activeError?<section className="technical-error" role="alert"><h2>Chưa hoàn tất kiểm tra</h2><p>{errorMessages[activeError.code]}</p><p>{activeError.code}: {activeError.message}</p><p>{runMode==='fixture'?'Lỗi kỹ thuật mô phỏng.':'Lỗi kỹ thuật.'} Chưa có kết luận về thông báo; đây không phải kết quả “chưa đủ bằng chứng”.</p>{activeError.retryable&&(canResume?<button disabled={busy} onClick={()=>void resume()}>Kiểm tra lại trạng thái</button>:<><p className="hint">Chỉ gửi lại khi bạn muốn tạo lần xử lý mới. Lần trước có thể đã phát sinh chi phí, kể cả khi mất kết nối.</p><button disabled={busy} onClick={()=>void submit(retry.current.text,retry.current.asset)}>{runMode==='fixture'?'Thử lại mô phỏng':'Gửi yêu cầu mới (có thể tốn phí)'}</button></>)}</section>
    :record&&recordView(record)==='progress'?<ProgressPanel status={record.status} slow={slow} onResume={()=>void resume()}/>
    :record?.status==='completed'&&record.result?<ResultTable result={record.result} client={client}/>:null}
    {(busy||slow||session.current)&&<button onClick={()=>void cancel()}>Hủy và xóa phiên kiểm tra</button>}
   </div>
  </main><footer><strong>TinChắc</strong><p>Căn cứ trước khi hành động. Kết quả có giới hạn theo nguồn và thời điểm đối chiếu.</p><span>Bản thử giao diện · {runMode??'Chưa xác định chế độ'}</span></footer>
 </>;
}
