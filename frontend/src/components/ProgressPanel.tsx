import type { Schema } from '../api/client';
import { progress } from '../api/presentation';
export function ProgressPanel({status,slow,onResume}:{status:Schema['CheckStatus'];slow:boolean;onResume:()=>void}) {
 return <section className="progress-panel" aria-live="polite" aria-label="Tiến trình mô phỏng"><h2>{slow?'Đang xử lý lâu':progress[status]}</h2><p>{slow?'Đã dừng tự động kiểm tra sau 120 giây. Kiểm tra lại cùng phiên khi bạn sẵn sàng.':'Đang chạy tình huống mẫu trong trình duyệt. Không gửi nội dung ra ngoài.'}</p>{slow&&<button onClick={onResume}>Kiểm tra lại trạng thái</button>}</section>;
}
