# Skills đóng gói

Các thư mục được lấy từ GitHub tại commit ghi dưới đây. Mỗi thư mục giữ giấy phép nguồn. Metadata `agents/openai.yaml` bổ sung chính sách gọi tường minh riêng của TinChắc. Gói dùng skill cấp dự án, không kèm hook cài đặt của upstream.

| Skill | Repo / commit | Đường dẫn upstream | Giấy phép |
|---|---|---|---|
| writing-plans | [obra/superpowers](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7) | `skills/writing-plans` | MIT |
| handoff | [mattpocock/skills](https://github.com/mattpocock/skills/tree/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d) | `skills/productivity/handoff` | MIT |
| ponytail-review | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846) | `skills/ponytail-review` | MIT |
| impeccable | [pbakaus/impeccable](https://github.com/pbakaus/impeccable/tree/613fbf88e0ef08709eaf238653285f430250c0ea) | `.agents/skills/impeccable` | Apache 2.0 |

Gọi `$writing-plans` để lập kế hoạch, rồi chạy từng task bằng Codex. Những workflow Superpowers khác được nhắc trong skill thuộc plugin upstream đầy đủ. `$handoff` của Matt viết nháp vào thư mục tạm. Với checkpoint bền vững, giữ bản chính trong `docs/handoffs/`. Impeccable có launcher cục bộ, có thể tải engine ở lần chạy đầu.
