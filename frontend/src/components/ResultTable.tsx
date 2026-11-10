import type { ApiClient, Schema } from '../api/client';
import { displayDate, labels, temporal } from '../api/presentation';
import { EvidencePanel } from './EvidencePanel';
import { Icon } from './Icon';
export const modeNames: Record<Schema['RunMode'], string> = {
 fixture: 'Fixture · Chế độ mô phỏng', replay: 'Replay · Kết quả đã lưu', live: 'Live · Xử lý trực tiếp',
};
export function ResultTable({ result, client }: { result: Schema['CheckResult']; client: ApiClient }) {
 return <section className="results" aria-labelledby="result-title"><h2 id="result-title">Phiếu đối chiếu</h2><p className="result-message">{result.summary.message}</p>
  <p className="hint">Đối chiếu lúc {displayDate(result.as_of)} (UTC+7) · {modeNames[result.run_mode]}</p>
  <ul className="summary-counts" aria-label="Tổng hợp kết quả">{Object.entries(labels).map(([label,text])=><li key={label}><strong>{result.summary[label as Schema['Label']]}</strong> {text.toLocaleLowerCase('vi-VN')}</li>)}</ul>
  {result.warnings.length>0&&<aside aria-label="Lưu ý hệ thống"><h3>Lưu ý về lần kiểm tra</h3><ul>{result.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul><p className="hint">Lưu ý hệ thống không phải kết luận lừa đảo.</p></aside>}
  <table><caption className="sr-only">Kết quả theo từng phát biểu</caption><thead><tr><th scope="col">Chi tiết đối chiếu</th><th scope="col">Nhận định &amp; căn cứ</th></tr></thead><tbody>{result.claims.map((claim)=><tr key={claim.claim_id}><th scope="row"><span className="mobile-label">Chi tiết đối chiếu</span>{claim.statement}</th><td><span className={'verdict '+claim.label}><Icon kind={claim.label}/>{labels[claim.label]}</span><p>{claim.explanation}</p><p className="temporal">Thời gian: {temporal[claim.temporal_status]}{claim.temporal_status==='expired'&&' — hết hạn không chứng minh giả mạo.'}</p>{claim.evidence.length ? claim.evidence.map((e,index)=><EvidencePanel key={claim.claim_id+index} evidence={e} client={client} summary={result.sources.find(source=>source.version_id===e.version_id)}/>) : <p className="hint">Chưa có trích dẫn đủ căn cứ cho chi tiết này. Nguồn không đề cập không có nghĩa là mâu thuẫn.</p>}</td></tr>)}</tbody></table>
  <div className="source-register"><h3>Phạm vi nguồn đã đối chiếu</h3><p>Kho <span className="identifier">{result.corpus_version}</span>, cập nhật lúc {displayDate(result.corpus_updated_at)} (UTC+7). Có {result.sources.length} nguồn kèm kết quả.</p>{result.sources.length>0?<ul>{result.sources.map(source=><li key={source.version_id}>{source.title} · {source.is_fixture?'Mô phỏng':'Nguồn công khai'} · Phiên bản <span className="identifier">{source.version_id}</span> · Công bố {displayDate(source.published_at)} · Lưu {displayDate(source.retrieved_at)} (UTC+7)</li>)}</ul>:<p>Chưa có nguồn đủ căn cứ để trích dẫn. Điều này không có nghĩa là thông báo sai hoặc kho không có nguồn.</p>}<p className="hint">Kết quả giới hạn trong kho nguồn và thời điểm trên, không bao phủ mọi thông báo DUT. Snapshot là bản đã lưu; TinChắc không xác nhận người gửi, chủ tài khoản hoặc an toàn của giao dịch.</p></div>
  <aside className="next-steps"><h3>Bước kiểm tra tiếp theo</h3><ul>{result.next_steps.map((step,index)=><li key={index}>{step}</li>)}</ul></aside>
 </section>;
}
