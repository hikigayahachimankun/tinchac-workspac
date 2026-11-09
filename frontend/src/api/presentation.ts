import type { Schema, CheckRecord } from './client';
export const labels = {
  supported: 'Được nguồn hỗ trợ',
  contradicted: 'Mâu thuẫn với nguồn',
  insufficient_evidence: 'Chưa đủ bằng chứng',
} satisfies Record<Schema['Label'], string>;
export const temporal = {
  active: 'Trong thời gian áp dụng', expired: 'Đã hết hạn', not_yet_active: 'Chưa đến thời gian áp dụng',
  unknown: 'Chưa rõ thời hạn', not_applicable: 'Không áp dụng thời hạn',
} satisfies Record<Schema['TemporalStatus'], string>;
export const progress = {
  queued: 'Đã tiếp nhận', extracting: 'Đang tách chi tiết', retrieving: 'Đang tìm nguồn trong kho', verifying: 'Đang đối chiếu bằng chứng',
  completed: 'Đã hoàn tất', failed: 'Gặp lỗi kỹ thuật',
} satisfies Record<Schema['CheckStatus'], string>;
export const errorMessages = {
  INVALID_INPUT:'Nội dung chưa hợp lệ. Kiểm tra lại thông báo rồi gửi lại.',
  INPUT_TOO_LARGE:'Nội dung quá dài. Rút ngắn còn tối đa 6.000 ký tự.',
  UNSUPPORTED_MEDIA:'Định dạng chưa hỗ trợ. Hãy nhập văn bản.',
  RESOURCE_NOT_FOUND:'Không tìm thấy phiên kiểm tra hoặc quyền truy cập. Hãy bắt đầu lại.',
  RESOURCE_EXPIRED:'Phiên kiểm tra đã hết thời gian lưu. Hãy bắt đầu lại.',
  ASSET_NOT_READY:'Ảnh chưa xử lý xong. Hãy chờ hoặc nhập văn bản.',
  OCR_FAILED:'Không đọc được chữ từ ảnh. Hãy nhập văn bản.',
  NO_CHECKABLE_CLAIM:'Chưa có chi tiết để đối chiếu. Hãy nhập thông báo cụ thể hơn.',
  TOO_MANY_CLAIMS:'Có quá nhiều chi tiết. Hãy chia thông báo thành các phần ngắn.',
  RATE_LIMITED:'Có quá nhiều yêu cầu. Hãy thử lại sau.',
  BUDGET_EXCEEDED:'Đã hết hạn mức xử lý. Hãy thử lại khi hạn mức được bổ sung.',
  PROVIDER_TIMEOUT:'Dịch vụ phản hồi quá lâu. Bạn có thể thử lại.',
  PROVIDER_BAD_OUTPUT:'Dịch vụ trả dữ liệu không hợp lệ. Bạn có thể thử lại.',
  CORPUS_UNAVAILABLE:'Kho nguồn đang không truy cập được. Hãy thử lại sau.',
  JOB_INTERRUPTED:'Phiên xử lý bị gián đoạn. Hãy chủ động gửi lại.',
  INTERNAL_ERROR:'Đã có lỗi kỹ thuật. Hãy thử lại sau.',
} satisfies Record<Schema['ErrorCode'], string>;
export function recordView(record: CheckRecord): 'result' | 'error' | 'progress' {
  if (record.status === 'failed') return 'error';
  if (record.status === 'completed') return 'result';
  return 'progress';
}
export function textError(text: string, consent: boolean) {
  const length = Array.from(text.normalize('NFC').trim()).length;
  if (length < 20 || length > 6000) return 'Nhập từ 20 đến 6.000 ký tự để kiểm tra.';
  if (!consent) return 'Hãy xác nhận bạn đã che thông tin cá nhân trước khi tiếp tục.';
  return null;
}
export function displayDate(value: string | null) {
  if (!value) return 'Chưa rõ ngày công bố';
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value.split('-').reverse().join('/');
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date(value));
}
