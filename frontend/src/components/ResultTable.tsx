import type { ApiClient, Schema } from '../api/client';
import { displayDate, labels, temporal } from '../api/presentation';
import { EvidencePanel } from './EvidencePanel';
import { Icon } from './Icon';
export function ResultTable({ result, client }: { result: Schema['CheckResult']; client: ApiClient }) {
 return <section className="results" aria-labelledby="result-title"><h2 id="result-title">Phiếu đối chiếu</h2><p className="result-message">{result.summary.message}</p>
  <p className="hint">Đối chiếu lúc {displayDate(result.as_of)} (giờ Việt Nam) · Chế độ mô phỏng</p>
  <ul className="summary-counts" aria-label="Tổng hợp kết quả">{Object.entries(labels).map(([label,text])=><li key={label}><strong>{result.summary[label as Schema['Label']]}</strong> {text.toLocaleLowerCase('vi-VN')}</li>)}</ul>
  <table><caption className="sr-only">Kết quả theo từng phát biểu trong tình huống mô phỏng</caption><thead><tr><th scope="col">Chi tiết đối chiếu</th><th scope="col">Nhận định &amp; căn cứ</th></tr></thead><tbody>{result.claims.map((claim)=><tr key={claim.claim_id}><th scope="row"><span className="mobile-label">Chi tiết đối chiếu</span>{claim.statement}</th><td><span className={'verdict '+claim.label}><Icon kind={claim.label}/>{labels[claim.label]}</span><p>{claim.explanation}</p><p className="temporal">Thời gian: {temporal[claim.temporal_status]}</p>{claim.evidence.length ? claim.evidence.map((e,index)=><EvidencePanel key={claim.claim_id+index} evidence={e} client={client}/>) : <p className="hint">Chưa có trích dẫn đủ căn cứ cho chi tiết này.</p>}</td></tr>)}</tbody></table>
  <div className="source-register"><h3>Phạm vi nguồn đã đối chiếu</h3><p>{result.sources.length} nguồn trong kho <span className="identifier">{result.corpus_version}</span>, cập nhật lúc {displayDate(result.corpus_updated_at)} (giờ Việt Nam).</p><ul>{result.sources.map(source=><li key={source.version_id}>{source.title} · {source.is_fixture?'Mô phỏng':'Nguồn công khai'} · Lưu {displayDate(source.retrieved_at)}</li>)}</ul><p className="hint">Chỉ đối chiếu trong snapshot của ví dụ. TinChắc không xác nhận người gửi, chủ tài khoản hoặc an toàn của giao dịch.</p></div>
  <aside className="next-steps"><h3>Bước kiểm tra tiếp theo</h3><ul>{result.next_steps.map(step=><li key={step}>{step}</li>)}</ul></aside>
 </section>;
}
