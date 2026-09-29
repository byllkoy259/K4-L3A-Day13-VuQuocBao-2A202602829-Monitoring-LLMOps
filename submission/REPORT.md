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
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
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
| `validate_logs.py` | 30/100 (21 record; 20 thiếu field bắt buộc; 20 thiếu enrichment; 0 correlation ID) | | Đúng như dự kiến fail do chưa làm TODO CP1 |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel | | Chỉ kiểm tra contract trong `config/dashboard.yaml`, chưa chứng minh dashboard runtime |
| `pytest` | 22 passed in 2.26s | | Public tests đã pass ở baseline |
| Số traces hợp lệ | | | |
| Số PII leak | 0 (validator) | | Xem ghi chú CP0 bên dưới |
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
- PII: `logging_config.py` chưa đăng ký `scrub_event`. Kết quả 0 leak chưa đáng tin, vì workload mẫu có thể không chứa PII. Cần kiểm tra lại bằng input có PII giả ở CP1.

**Kết quả `validate_dashboard.py` và `pytest`:** dashboard 6/6 panel hợp lệ; 22 test pass.

**Bước tiếp theo:** làm các TODO CP1, xóa hoặc đổi tên `data/logs.jsonl` cũ trước khi đo lại để log chưa scrub không bị tính.

**Evidence baseline:** lưu output terminal của bốn lệnh trên (dạng `.txt` hoặc ảnh) vào `submission/evidence/` với tên `00-baseline-*` để phân biệt với evidence cuối.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
- **Các metadata được ghi vào structured log:**
- **Cách bảo đảm PII được scrub trước khi ghi:**
- **Cách kiểm chứng kết quả:**

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
