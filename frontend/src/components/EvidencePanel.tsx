import { useState } from 'react';
import type { ApiClient, Schema, SourcePublic } from '../api/client';
import { ApiError } from '../api/client';
import { displayDate, errorMessages } from '../api/presentation';
// Only approved public source metadata may supply links. Claims/next_steps stay text.
export function sourceLink(source: Schema['SourceSummary']): string | null {
  if(source.is_fixture) return null;
  try {
    const url=new URL(source.canonical_url);
    return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password ? url.href : null;
  } catch { return null; }
}
export function EvidencePanel({ evidence, client, summary }: { evidence: Schema['EvidenceRef']; client: ApiClient; summary?: Schema['SourceSummary'] }) {
  const [opened,setOpened] = useState(false);
  const [source,setSource] = useState<SourcePublic | null>(null);
  const [error,setError] = useState<string | null>(null);
  const [loading,setLoading] = useState(false);
  async function load() {
    if(source || loading) return;
    setLoading(true); setError(null);
    try { setSource(await client.getSource(evidence.version_id)); }
    catch(error) { setError(error instanceof ApiError ? errorMessages[error.detail.code] : 'Không tải được snapshot. Hãy thử lại.'); }
    finally { setLoading(false); }
  }
  const metadata=source??(opened?summary:undefined);
  const href=source?sourceLink(source):null;
  return <details className="evidence" onToggle={event=>{setOpened(event.currentTarget.open);if(event.currentTarget.open) void load();}}><summary>Xem bằng chứng</summary>
    <div className="evidence-sheet"><h3>Trích đoạn trong snapshot</h3><blockquote>{evidence.quote}</blockquote>
    <p className="hint">Phiên bản <span className="identifier">{evidence.version_id}</span> · Đoạn <span className="identifier">{evidence.chunk_id}</span></p>
    {loading&&<p role="status">Đang mở snapshot đã lưu…</p>}
    {error&&<div role="alert"><p>{error} Trích đoạn trong kết quả vẫn hiển thị ở trên.</p><button disabled={loading} onClick={()=>void load()}>Thử tải lại snapshot</button></div>}
    {metadata&&<><p className="source-title">{metadata.title}</p><dl className="metadata"><div><dt>Ngày công bố</dt><dd>{displayDate(metadata.published_at)}</dd></div><div><dt>Lưu snapshot</dt><dd>{displayDate(metadata.retrieved_at)} (UTC+7)</dd></div><div><dt>Phiên bản</dt><dd>{metadata.version_id}</dd></div></dl></>}
    {source&&<><p className="hint">{source.is_fixture?'Nguồn mô phỏng. ':''}Snapshot đã lưu, không phải lần kiểm tra trực tiếp trang gốc. Khi trang gốc mất, bạn vẫn có thể đọc bản này.</p>
    {href?<a href={href} target="_blank" rel="noopener noreferrer">Mở trang nguồn gốc (tab mới)<span className="source-url">{source.canonical_url}</span></a>:<p className="hint">{source.is_fixture?'URL gốc — định danh mô phỏng':'URL nguồn không mở được an toàn'}<span className="source-url">{source.canonical_url}</span></p>}
    <details className="snapshot"><summary>Đọc nội dung snapshot</summary><p>{source.text}</p></details></>}
    </div>
  </details>;
}
