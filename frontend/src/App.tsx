import { useMemo, useRef, useState, useEffect } from 'react';
import { ApiError, createHttpClient, createMockClient, pollCheck } from './api/client';
import type { CheckRecord, Scenario, Schema } from './api/client';
import requestExample from '../../contracts/examples/check_create.json';
import { errorMessages, recordView } from './api/presentation';
import { InputForm } from './components/InputForm';
import { ProgressPanel } from './components/ProgressPanel';
import { ResultTable } from './components/ResultTable';
export default function App() {
 const [scenario,setScenario] = useState<Scenario>('mixed');
 const mockMode = import.meta.env.VITE_API_MODE === 'mock';
 const client = useMemo(()=>mockMode ? createMockClient(scenario) : createHttpClient(),[scenario,mockMode]);
 const [record,setRecord] = useState<CheckRecord|null>(null);
 const [busy,setBusy] = useState(false);
 const [slow,setSlow] = useState(false);
 const [error,setError] = useState<Schema['ErrorDetail']|null>(null);
 const session = useRef<{id:string;token:string}|null>(null);
 const output = useRef<HTMLDivElement>(null);
 const retry = useRef('');
 useEffect(()=>{ if(error || record?.status==='completed' || record?.status==='failed' || slow) output.current?.focus(); },[error,record?.status,slow]);
 async function monitor() {
   if(!session.current) return;
   const status=await pollCheck(client,session.current.id,session.current.token,setRecord);
   setSlow(status==='slow');
 }
 function fail(error:unknown) { setError(error instanceof ApiError?error.detail:{code:'INTERNAL_ERROR',message:'Có lỗi kỹ thuật.',retryable:true,details:{}}); }
 async function submit(text:string) {
   retry.current=text;setRecord(null);setError(null);setSlow(false);setBusy(true);
   try {
     const response=await client.createCheck({...requestExample, schema_version:'1.0',input_mode:'text', confirmed_text:text,asset_id:null,asset_token:null,consent_to_process:true});
     session.current={id:response.check.check_id,token:response.access_token};
     setRecord(response.check); await monitor();
   } catch(error) { fail(error); } finally { setBusy(false); }
 }
 async function resume() { setSlow(false);setBusy(true);try { await monitor(); }catch(error){fail(error);}finally{setBusy(false);} }
 const activeError=error??(record?.status==='failed'?record.error:null);
 return <><a className="skip-link" href="#main">Đến nội dung chính</a><header className="site-header"><a href="#main" className="wordmark">TinChắc<span className="brand-dot" aria-hidden="true">.</span></a><span>Đối chiếu thông báo học vụ</span></header>
  <div className="fixture-banner" role="note"><strong>Chế độ mô phỏng</strong><span>Dữ liệu và kết quả mẫu. Không dùng để quyết định nộp hồ sơ hoặc chuyển tiền.</span></div>
  <main id="main"><InputForm busy={busy||slow} mockMode={mockMode} scenario={scenario} onScenario={value=>{setScenario(value);setRecord(null);setError(null);session.current=null;}} onSubmit={submit}/>
   <div ref={output} role="region" tabIndex={-1} className="output" aria-label="Trạng thái đối chiếu">
    {activeError ? <section className="technical-error" role="alert"><h2>Chưa hoàn tất kiểm tra</h2><p>{errorMessages[activeError.code]}</p><p>{activeError.code}: {activeError.message}</p><p>Lỗi kỹ thuật mô phỏng. Chưa có kết luận về thông báo; đây không phải kết quả “chưa đủ bằng chứng”.</p>{activeError.retryable?<button disabled={busy} onClick={()=>void submit(retry.current)}>Thử lại mô phỏng</button>:<p className="hint">Sửa nội dung hoặc chọn tình huống khác rồi gửi lại.</p>}</section>
    : record && recordView(record)==='progress' ? <ProgressPanel status={record.status} slow={slow} onResume={()=>void resume()}/>
    : record?.status==='completed' && record.result ? <ResultTable result={record.result} client={client}/> : null}
   </div>
  </main><footer><strong>TinChắc</strong><p>Căn cứ trước khi hành động. Kết quả có giới hạn theo nguồn và thời điểm đối chiếu.</p><span>Bản thử giao diện · Fixture v1</span></footer>
 </>;
}
