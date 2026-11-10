import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { Scenario, Schema } from '../api/client';
import { textError } from '../api/presentation';
import fixtureTexts from '../api/fixture-texts.json';
export const scenarioNames: Record<Scenario, string> = {
  mixed:'Kết quả hỗn hợp — ba nhãn', original:'Ví dụ T01 — mâu thuẫn', supported:'Chi tiết được hỗ trợ', nei:'Toàn bộ chưa đủ bằng chứng', expired:'Trạng thái hết hạn (giả lập)', failed:'Lỗi kỹ thuật khi xử lý', request_error:'Lỗi khi tiếp nhận',
};
const sample = 'Học bổng Minh Họa 2026: 7 triệu/suất. Đóng phí giữ suất 300.000 đồng.';
export function InputForm({ busy, mockMode, runMode, scenario, onScenario, onSubmit }: { busy: boolean; mockMode: boolean; runMode?: Schema['RunMode'] | null; scenario: Scenario; onScenario: (value: Scenario) => void; onSubmit: (text: string) => void }) {
  const [text,setText] = useState('');
  const [consent,setConsent] = useState(false);
  const [error,setError] = useState<string | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const consentRef = useRef<HTMLInputElement>(null);
  function submit(event: FormEvent) {
    event.preventDefault(); const message = textError(text,consent); setError(message);
    if (message) { (textError(text,true) ? input.current : consentRef.current)?.focus(); return; }
    onSubmit(text.normalize('NFC').trim());
  }
  return <section className="input-section" aria-labelledby="input-title"><h1 id="input-title">Kiểm tra thông báo</h1>
    <p className="intro">Đối chiếu từng chi tiết học bổng và thu phí trong phạm vi nguồn công khai DUT.</p>

    <form onSubmit={submit} noValidate>
      <label htmlFor="notice">Nội dung thông báo</label>
      <p className="hint" id="text-hint">Dán nội dung cần đối chiếu. Che tên, mã sinh viên, số tài khoản và thông tin cá nhân.</p>
      <textarea ref={input} id="notice" value={text} onChange={e=>{setText(e.target.value);setError(null);}} disabled={busy} aria-invalid={!!error && !!textError(text,true)} aria-describedby={'text-hint char-count'+(error?' form-error':'')} placeholder="Ví dụ: Học bổng Minh Họa 2026: 7 triệu/suất…" rows={6}/>
      <div className="text-tools"><button type="button" className="text-button" disabled={busy} onClick={()=>{setText(sample);setError(null);input.current?.focus();}}>Điền nội dung mẫu</button><span id="char-count">{Array.from(text.normalize('NFC')).length.toLocaleString('vi-VN')} / 6.000 ký tự</span></div>
      <label className="consent"><input ref={consentRef} type="checkbox" checked={consent} disabled={busy} onChange={e=>{setConsent(e.target.checked);setError(null);}} aria-describedby={error?'form-error':undefined}/>Tôi đã che thông tin cá nhân và đồng ý xử lý nội dung này.</label>
      {error && <p id="form-error" className="form-error" role="alert">{error}</p>}
      <button className="primary" type="submit" disabled={busy}>{busy?'Đang xử lý…':runMode==='fixture'||mockMode?'Kiểm tra mô phỏng':'Kiểm tra thông báo'}<svg className="button-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6"/></svg></button>
      <p className="hint">{runMode==='fixture'||mockMode?'Kết quả là mẫu cố định; nội dung bạn nhập chưa được phân tích.':'Chỉ gửi khi bạn đã kiểm tra nội dung. Mỗi lần gửi có thể phát sinh chi phí xử lý.'}</p>
    </form>
    {(runMode==='fixture'||mockMode)&&<details className="demo-settings"><summary>Tình huống mô phỏng</summary><label htmlFor="scenario">Chọn kết quả mẫu</label><select id="scenario" value={scenario} disabled={busy} onChange={e=>{const value=e.target.value as Scenario;onScenario(value);if(!mockMode && value !== 'request_error') setText(fixtureTexts[value]);}}>{Object.entries(scenarioNames).filter(([key])=>mockMode || (key!=='request_error' && key!=='expired')).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select><p className="hint">{mockMode ? 'Kết quả cố định theo tình huống; mock giao diện không gọi backend.' : 'Gửi tới FastAPI thật, xử lý bằng fixture. Chọn tình huống để điền văn bản định danh; không dùng Gemini.'}</p></details>}
  </section>;
}
