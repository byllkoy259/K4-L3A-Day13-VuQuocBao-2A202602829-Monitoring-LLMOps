# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng cảm nhận được (chậm, lỗi, tốn tiền bất thường), không dựa trên tên hàm nội bộ. Định nghĩa máy đọc được nằm ở [config/alert_rules.yaml](../config/alert_rules.yaml); SLO ở [config/slo.yaml](../config/slo.yaml). Nguồn dữ liệu là `data/logs.jsonl`, nối sang trace bằng `correlation_id`.

## Alert 1

- Tên: `high_latency_p95`
- Severity: P2
- Duration: 5 phút
- Kênh thông báo: Slack `#day13-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` (request thành công có `latency_ms <= 3000`, target 99%, error budget 1%)
- Điều kiện và thời gian duy trì: P95 của `latency_ms` (event `response_sent`) > 3000 ms liên tục 5 phút
- Ảnh hưởng tới người dùng: câu trả lời đến chậm, mỗi request chậm tiêu thụ error budget của SLO
- Ba bước kiểm tra đầu tiên:
  1. Dashboard panel Latency: P95/P99 tăng từ lúc nào, TTFT có tăng theo không (TTFT ổn mà tổng latency tăng thì chậm nằm ở retrieval hoặc phần sinh dài).
  2. Lọc `data/logs.jsonl` lấy một `correlation_id` có `latency_ms` cao nhất trong khoảng đó.
  3. Mở trace có cùng `correlation_id` trong Langfuse, so sánh thời gian span `retrieval` với `llm-generate` để xác định span chậm; kiểm tra `GET /health` xem incident `rag_slow` có đang bật không.
- Mitigation tạm thời: nếu do retrieval chậm thì tắt hoặc bypass retrieval (trả lời fallback), tắt incident giả lập (`python scripts/inject_incident.py --scenario rag_slow --disable`), giảm concurrency hoặc scale thêm worker; theo dõi lại P95 sau 10 phút.
- Owner: vu-quoc-bao (on-call)

## Alert 2

- Tên: `high_error_rate`
- Severity: P1
- Duration: 5 phút
- Kênh thông báo: Slack `#day13-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` và guardrail `error_rate_pct_max: 2`, `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: `count(request_failed) / count(request_received) * 100 > 2` trong 5 phút liên tục
- Ảnh hưởng tới người dùng: request trả HTTP 500, người dùng không nhận được câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Dashboard panel Errors: xem error rate, breakdown theo `error_type` và retrieval success (`tool_success`).
  2. Lọc log `request_failed`, lấy `correlation_id`, đọc `error_type` và `payload.detail` (ví dụ `RuntimeError: Vector store timeout`).
  3. Mở trace cùng `correlation_id`, xem span `retrieval` có trạng thái lỗi không, đối chiếu `GET /health` (incident `tool_fail`).
- Mitigation tạm thời: tắt incident/khôi phục vector store, bật fallback trả lời không có retrieval, rollback thay đổi gần nhất (kể cả prompt: đưa label `production` về version trước bằng `python scripts/manage_prompts.py promote <version>`).
- Owner: vu-quoc-bao (on-call)

## Alert 3

- Tên: `cost_per_request_spike`
- Severity: P2
- Duration: 10 phút
- Kênh thông báo: Slack `#day13-alerts`
- SLI/SLO liên quan: guardrail `daily_cost_usd_max: 2.5` (chi phí trung bình baseline ~0.002 USD/request)
- Điều kiện và thời gian duy trì: `mean(cost_usd)` trên event `response_sent` > 0.005 USD/request (~2.5 lần baseline) liên tục 10 phút
- Ảnh hưởng tới người dùng: người dùng không thấy ngay, nhưng chi phí vận hành tăng mạnh và có thể vượt ngân sách ngày
- Ba bước kiểm tra đầu tiên:
  1. Dashboard panel Cost và Tokens: `tokens_out` hoặc `tokens_in` có tăng đột biến không, bắt đầu từ lúc nào.
  2. Lọc `response_sent` có `tokens_out` lớn nhất, lấy `correlation_id`.
  3. Mở trace cùng `correlation_id`, xem generation `llm-generate` (usage, cost) và prompt name/version/label; kiểm tra có vừa đổi version prompt hoặc bật incident `cost_spike` không.
- Mitigation tạm thời: rollback prompt `production` về version trước, giới hạn `max_tokens`/độ dài câu trả lời, chuyển feature tốn kém sang model rẻ hơn hoặc rate-limit; theo dõi lại cost trung bình sau 15 phút.
- Owner: vu-quoc-bao (on-call)
