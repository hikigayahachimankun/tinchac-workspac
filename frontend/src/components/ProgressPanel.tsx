import type { Schema } from '../api/client';
import { progress } from '../api/presentation';
export function ProgressPanel({status,slow,onResume}:{status:Schema['CheckStatus'];slow:boolean;onResume:()=>void}) {
 return <section className="progress-panel" aria-live="polite" aria-label="Tiến trình đối chiếu"><h2>{slow?'Đang xử lý lâu':progress[status]}</h2><p>{slow?'Đã dừng tự động kiểm tra sau 120 giây. Kiểm tra lại cùng phiên khi bạn sẵn sàng.':'Đang xử lý phiên đã tiếp nhận. Chưa có kết luận về thông báo.'}</p><p className="hint">Kiểm tra trạng thái không tạo yêu cầu phân tích mới.</p>{slow&&<button onClick={onResume}>Kiểm tra lại trạng thái</button>}</section>;
}
