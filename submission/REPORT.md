# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Vũ Quốc Bảo
- **MSSV:** 2A202602829
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/byllkoy259/K4-L3A-Day13-VuQuocBao-2A202602829-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2a202602829`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 (21 record; 20 thiếu field bắt buộc; 20 thiếu enrichment; 0 correlation ID) | 100/100 (23 record; 0 thiếu field; 0 thiếu enrichment; 11 correlation ID; 0 PII leak) | Đúng như dự kiến fail do chưa làm TODO CP1; sau CP1 đạt 100/100 (yêu cầu ≥ 80) |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel | HỢP LỆ: 6/6 panel | Chỉ kiểm tra contract trong `config/dashboard.yaml`, chưa chứng minh dashboard runtime |
| `pytest` | 22 passed in 2.26s | 30 passed in 3.17s (thêm 8 test cho PII và correlation/logging) | Public tests đã pass ở baseline |
| Số traces hợp lệ | | | |
| Số PII leak | 0 (validator; xem giải thích ở CP0) | 0 (validator, sau khi gửi request chứa 4 loại PII giả) | Xem ghi chú CP0 bên dưới |
| Latency P95 / TTFT P95 | Chưa tính từ log (chỉ có 10 request mẫu: 1 request 1665.1 ms, 9 request còn lại 390.2–521.5 ms) | | Request đầu chậm nhất, nghi do khởi động nguội |
| Retrieval success rate | | | |

### Baseline CP0

**Môi trường:** Windows, Python 3.11.9, virtualenv `.venv`, chạy API bằng `uvicorn`, workload bằng `python scripts/load_test.py` (10 request, feature `qa` và `summary`).

**Kết quả load test:** cả 10 request trả HTTP 200. Cột correlation ID in ra `MISSING` ở cả 10 request, vì `app/middleware.py` còn hard-code `correlation_id = "MISSING"`.

**Kết quả `validate_logs.py`:**

| Tiêu chí | Kết quả |
|---|---|
| Required fields (`ts`, `level`, ...) | FAILED (20/21 record thiếu) |
| Correlation ID propagation | FAILED (0 unique ID, cần ≥ 2) |
| Log enrichment (`user_id_hash`, ...) | FAILED (20/21 record thiếu) |
| PII scrubbing | PASSED (0 leak) |
| **Điểm ước tính** | **30/100** |

**Nguyên nhân (đối chiếu source):**
- Correlation ID: `middleware.py` chưa xóa contextvars, chưa đọc/sinh `x-request-id`, chưa bind ID, chưa trả header.
- Enrichment: `main.py` chưa `bind_contextvars(user_id_hash, session_id, feature, model, env)`.
- PII: `logging_config.py` chưa đăng ký `scrub_event`. Workload mẫu có chứa email, nhưng kết quả vẫn 0 leak vì log chỉ ghi `message_preview` do `summarize_text()` đã gọi `scrub_text` sẵn; `scrub_event` chưa được bật nên các field khác (ví dụ `detail` của lỗi) vẫn chưa được bảo vệ. Vì vậy 0 leak ở baseline chưa chứng minh pipeline scrub hoạt động, và cần kiểm tra lại bằng input có PII giả ở CP1.

**Kết quả `validate_dashboard.py` và `pytest`:** dashboard 6/6 panel hợp lệ; 22 test pass.

**Bước tiếp theo:** làm các TODO CP1, xóa hoặc đổi tên `data/logs.jsonl` cũ trước khi đo lại để log chưa scrub không bị tính.

**Evidence baseline:** lưu output terminal của bốn lệnh trên (dạng `.txt` hoặc ảnh) vào `submission/evidence/` với tên `00-baseline-*` để phân biệt với evidence cuối.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` ([app/middleware.py](../app/middleware.py)) gọi `clear_contextvars()` ở đầu mỗi request để không rò context giữa các request. Sau đó nhận `x-request-id` từ header nếu khớp `[A-Za-z0-9_-]{1,64}`, nếu không thì sinh `req-<8-hex>` (từ `uuid4`). Giới hạn ký tự và độ dài để header không thể chèn dòng log giả hoặc làm phình log. ID được `bind_contextvars` nên mọi log trong request tự mang `correlation_id`, đồng thời lưu ở `request.state.correlation_id` để truyền vào agent/trace. Response trả lại header `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** ngoài `ts`, `level`, `service`, `event`, `correlation_id`, handler `/chat` ([app/main.py](../app/main.py)) bind thêm `user_id_hash` (SHA-256 cắt 12 ký tự, không lưu `user_id` thô), `session_id`, `feature`, `model`, `env` trước log `request_received`. Log `response_sent` có thêm `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` ([app/logging_config.py](../app/logging_config.py)) được đăng ký trong chuỗi processor **trước** `JsonlFileProcessor` và `JSONRenderer`, nên PII bị che trước khi serialize và trước khi ghi file. Processor duyệt đệ quy mọi giá trị chuỗi (kể cả `payload` lồng nhau, list, `detail` của lỗi), không chỉ `payload`. Các field do app tự sinh (`ts`, `level`, `correlation_id`, `user_id_hash`) được bỏ qua vì hash 12 ký tự có thể toàn chữ số và bị nhầm với CCCD. [app/pii.py](../app/pii.py) có rule cho email, điện thoại Việt Nam, CCCD 12 số, thẻ 16 số và thêm passport (`[A-Z]` + 7 số).
- **Cách kiểm chứng kết quả:**
  - `python scripts/validate_logs.py` đạt 100/100 trên log sạch (đã đổi tên log baseline trước khi đo lại): [evidence/02-log-validator.txt](evidence/02-log-validator.txt).
  - Gửi request có `x-request-id: req-4ab223bd` và message chứa thẻ, CCCD, email, điện thoại giả. Log `request_received` chỉ còn `[REDACTED_CREDIT_CARD] [REDACTED_CCCD] [REDACTED_EMAIL] [REDACTED_PHONE_VN]`, và `Select-String` các giá trị thô trong `data/logs.jsonl` không trả về dòng nào: ![PII redaction](evidence/05-pii-redaction.png)
  - Dòng `response_sent` cùng `correlation_id` `req-4ab223bd` có đủ metadata: ![Structured log](evidence/04-structured-log.png)
  - Test tự động: [tests/test_logging_correlation.py](../tests/test_logging_correlation.py) (sinh và tái sử dụng ID, ID không an toàn bị thay, enrichment, không rò context giữa request, không còn PII thô trong file log) và [tests/test_pii.py](../tests/test_pii.py) (email, điện thoại, CCCD, thẻ, passport, văn bản sạch). Kết quả: [evidence/01-pytest.txt](evidence/01-pytest.txt), 30 passed.
- **Hạn chế đã biết:** `message_preview` bị cắt ở 80 ký tự sau khi scrub (`summarize_text`), nên với message dài thì các loại PII ở cuối không hiện trong preview (đã được che, chỉ là bị cắt). Chưa có rule cho địa chỉ.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
