import { useState } from 'react';
import type { ApiClient, Schema, SourcePublic } from '../api/client';
import { ApiError } from '../api/client';
import { displayDate, errorMessages } from '../api/presentation';
export function EvidencePanel({ evidence, client }: { evidence: Schema['EvidenceRef']; client: ApiClient }) {
  const [source,setSource] = useState<SourcePublic | null>(null);
  const [error,setError] = useState<string | null>(null);
  const [loading,setLoading] = useState(false);
  async function load() {
    if(source || loading) return;
    setLoading(true); setError(null);
    try { setSource(await client.getSource(evidence.version_id)); }
    catch(error) { setError(error instanceof ApiError ? errorMessages[error.detail.code] : 'Không tải được snapshot. Hãy thử mở lại chi tiết.'); }
    finally { setLoading(false); }
  }
  return <details className="evidence" onToggle={event=>{if(event.currentTarget.open) void load();}}><summary>Xem bằng chứng</summary>
    <div className="evidence-sheet"><h3>Trích đoạn trong snapshot</h3><blockquote>{evidence.quote}</blockquote>
    {loading&&<p role="status">Đang mở snapshot mô phỏng…</p>}
    {error&&<p role="alert">{error}</p>}
    {source&&<><p className="source-title">{source.title}</p><dl className="metadata"><div><dt>Ngày công bố</dt><dd>{displayDate(source.published_at)}</dd></div><div><dt>Lưu snapshot</dt><dd>{displayDate(source.retrieved_at)} (giờ Việt Nam)</dd></div><div><dt>Phiên bản</dt><dd>{source.version_id}</dd></div></dl>
    <p className="hint">Nguồn mô phỏng. Snapshot đã lưu, không phải lần kiểm tra trực tiếp trang gốc.</p>
    <a href={source.canonical_url} target="_blank" rel="noopener noreferrer">URL gốc — định danh mô phỏng (mở tab mới)<span className="source-url">{source.canonical_url}</span></a>
    <details className="snapshot"><summary>Đọc nội dung snapshot</summary><p>{source.text}</p></details></>}
    </div>
  </details>;
}
