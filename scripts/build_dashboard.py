"""Dựng dashboard 6 panel (HTML + SVG, không cần thư viện ngoài) từ data/logs.jsonl.

Panel, đơn vị và threshold đọc trực tiếp từ config/dashboard.yaml.
Chạy: python scripts/build_dashboard.py [--minutes 60] [--out data/dashboard.html]
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402
from app.metrics import percentile  # noqa: E402

COLORS = ["#2563eb", "#16a34a", "#d97706", "#9333ea"]
W, H, PAD_L, PAD_R, PAD_T, PAD_B = 520, 220, 52, 14, 14, 30


def load_logs(path: Path, start: datetime) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            rec["_t"] = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if rec["_t"] >= start:
            rows.append(rec)
    return rows


def bucket(rows: list[dict], start: datetime, minutes: int, event: str) -> list[list[dict]]:
    out: list[list[dict]] = [[] for _ in range(minutes)]
    for r in rows:
        if r.get("event") == event:
            idx = int((r["_t"] - start).total_seconds() // 60)
            if 0 <= idx < minutes:
                out[idx].append(r)
    return out


def chart(
    series: list[tuple[str, list[float | None]]],
    threshold: float | None,
    unit: str,
    minutes: int,
    bars: bool = False,
) -> str:
    vals = [v for _, s in series for v in s if v is not None]
    top = max(vals + ([threshold] if threshold is not None else []) + [1e-9]) * 1.15
    pw, ph = W - PAD_L - PAD_R, H - PAD_T - PAD_B

    def x(i: float) -> float:
        return PAD_L + (i + 0.5) * pw / minutes

    def y(v: float) -> float:
        return PAD_T + ph - (v / top) * ph

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img">']
    for k in range(5):
        v = top * k / 4
        parts.append(f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="gl"/>')
        parts.append(f'<text x="{PAD_L - 6}" y="{y(v) + 4:.1f}" class="ax" text-anchor="end">{v:.4g}</text>')
    for k in range(0, minutes + 1, 10):
        px = PAD_L + k * pw / minutes
        parts.append(f'<text x="{px:.1f}" y="{H - 10}" class="ax" text-anchor="middle">-{minutes - k}m</text>')
    for n, (_, s) in enumerate(series):
        c = COLORS[n % len(COLORS)]
        if bars:
            bw = max(2.0, pw / minutes / len(series) - 1)
            for i, v in enumerate(s):
                if v:
                    bx = x(i) - bw * len(series) / 2 + n * bw
                    parts.append(
                        f'<rect x="{bx:.1f}" y="{y(v):.1f}" width="{bw:.1f}" height="{PAD_T + ph - y(v):.1f}" fill="{c}"/>'
                    )
        else:
            pts = [(x(i), y(v)) for i, v in enumerate(s) if v is not None]
            if len(pts) > 1:
                joined = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
                parts.append(f'<polyline fill="none" stroke="{c}" stroke-width="2" points="{joined}"/>')
            for a, b in pts:
                parts.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="2.5" fill="{c}"/>')
    if threshold is not None:
        parts.append(
            f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{y(threshold):.1f}" y2="{y(threshold):.1f}" class="thr"/>'
        )
        parts.append(
            f'<text x="{W - PAD_R}" y="{y(threshold) - 4:.1f}" class="thrt" text-anchor="end">'
            f"threshold {threshold:g} {html.escape(unit)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def legend(names: list[str]) -> str:
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{COLORS[i % len(COLORS)]}"></i>{html.escape(n)}</span>'
        for i, n in enumerate(names)
    ) + "</div>"


def stat(label: str, value: str, ok: bool | None) -> str:
    cls = "" if ok is None else (" ok" if ok else " bad")
    return f'<div class="stat{cls}"><b>{html.escape(value)}</b><small>{html.escape(label)}</small></div>'


def check(value: float, th: dict) -> bool:
    return value <= th["value"] if th["operator"] == "lte" else value >= th["value"]


CSS = """
body{font:14px system-ui,sans-serif;margin:0;padding:16px;background:#f8fafc;color:#0f172a}
h1{font-size:20px;margin:0 0 4px}.meta{color:#475569;margin-bottom:14px}
.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:14px}
section{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px}
h2{font-size:15px;margin:0 0 8px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px}
h2 small{color:#64748b;font-weight:400}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.stat{border:1px solid #e2e8f0;border-radius:6px;padding:4px 10px}
.stat b{display:block;font-size:16px}.stat small{color:#64748b}
.ok{border-color:#16a34a}.bad{border-color:#dc2626;background:#fef2f2}
svg{width:100%;height:auto}.gl{stroke:#e2e8f0}.ax{font-size:10px;fill:#64748b}
line.thr{stroke:#dc2626;stroke-dasharray:5 4;stroke-width:1.5}.thrt{font-size:10px;fill:#dc2626}
.legend{display:flex;gap:12px;font-size:12px;color:#475569}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}
"""


def main() -> int:
    configure_utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=None, help="mặc định lấy time_range_minutes trong dashboard.yaml")
    ap.add_argument("--end", default=None, help="mốc kết thúc cửa sổ (ISO, UTC), ví dụ 2026-09-29T09:50; mặc định là bây giờ")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "dashboard.html")
    ap.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    a = ap.parse_args()

    cfg = yaml.safe_load((REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
    minutes = a.minutes or cfg["time_range_minutes"]
    if a.end:
        end = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
    else:
        end = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
    start = end - timedelta(minutes=minutes)
    rows = [r for r in load_logs(a.logs, start) if r["_t"] < end]
    sent = bucket(rows, start, minutes, "response_sent")
    recv = bucket(rows, start, minutes, "request_received")
    failed = bucket(rows, start, minutes, "request_failed")
    panels = {p["id"]: p for p in cfg["panels"]}
    all_sent = [r for b in sent for r in b]
    all_recv = sum(len(b) for b in recv)
    all_failed = sum(len(b) for b in failed)
    cards: list[str] = []

    def card(pid: str, stats: str, body: str) -> None:
        p = panels[pid]
        th = p["threshold"]
        cards.append(
            f'<section><h2>{html.escape(p["title"])}<small>unit: {html.escape(p["unit"])} · '
            f'threshold {th["aggregation"]} {th["operator"]} {th["value"]}</small></h2>'
            f'<div class="stats">{stats}</div>{body}</section>'
        )

    # 1. latency
    lat = [r["latency_ms"] for r in all_sent]
    ttft = [r["ttft_ms"] for r in all_sent]
    p50, p95, p99, t95 = percentile(lat, 50), percentile(lat, 95), percentile(lat, 99), percentile(ttft, 95)

    def pl(q: int, key: str) -> list[float | None]:
        return [percentile([r[key] for r in b], q) if b else None for b in sent]

    th = panels["latency"]["threshold"]
    card(
        "latency",
        stat("P50", f"{p50:.0f} ms", None)
        + stat("P95", f"{p95:.0f} ms", check(p95, th))
        + stat("P99", f"{p99:.0f} ms", None)
        + stat("TTFT P95", f"{t95:.0f} ms", None),
        chart(
            [("P50", pl(50, "latency_ms")), ("P95", pl(95, "latency_ms")), ("P99", pl(99, "latency_ms")), ("TTFT P95", pl(95, "ttft_ms"))],
            th["value"], "ms", minutes,
        )
        + legend(["P50", "P95", "P99", "TTFT P95"]),
    )
    # 2. traffic
    per_min = [len(b) for b in recv]
    rate = all_recv / minutes
    th = panels["traffic"]["threshold"]
    card(
        "traffic",
        stat("requests", str(all_recv), None) + stat("avg rate", f"{rate:.2f} req/min", check(rate, th)),
        chart([("requests/min", [float(v) for v in per_min])], th["value"], "req/min", minutes, bars=True)
        + legend(["requests/min"]),
    )
    # 3. errors + retrieval success
    err_rate = all_failed / all_recv * 100 if all_recv else 0.0
    tools = [r for r in rows if r.get("tool_success") is not None]
    ok_tools = sum(1 for r in tools if r["tool_success"] is True)
    retr = ok_tools / len(tools) * 100 if tools else 100.0
    by_type: dict[str, int] = defaultdict(int)
    for b in failed:
        for r in b:
            by_type[r.get("error_type", "unknown")] += 1
    th = panels["errors"]["threshold"]
    er = [(len(f) / len(rv) * 100 if rv else 0.0) for f, rv in zip(failed, recv)]
    breakdown = ", ".join(f"{k}: {v}" for k, v in by_type.items()) or "none"
    card(
        "errors",
        stat("error rate", f"{err_rate:.2f} %", check(err_rate, th))
        + stat("retrieval success", f"{retr:.1f} %", retr >= 90)
        + stat("errors by type", breakdown, None),
        chart([("error rate %", er)], th["value"], "%", minutes, bars=True) + legend(["error rate %"]),
    )
    # 4. cost
    cost_m = [sum(r["cost_usd"] for r in b) for b in sent]
    total = sum(cost_m)
    th = panels["cost"]["threshold"]
    avg_cost = total / len(all_sent) if all_sent else 0
    card(
        "cost",
        stat("total", f"${total:.4f}", check(total, th)) + stat("avg / request", f"${avg_cost:.5f}", None),
        chart([("usd/min", cost_m)], th["value"], "usd", minutes, bars=True) + legend(["USD / minute"]),
    )
    # 5. tokens
    tin = [sum(r["tokens_in"] for r in b) for b in sent]
    tout = [sum(r["tokens_out"] for r in b) for b in sent]
    th = panels["tokens"]["threshold"]
    card(
        "tokens",
        stat("tokens in", str(sum(tin)), check(sum(tin), th)) + stat("tokens out", str(sum(tout)), check(sum(tout), th)),
        chart([("tokens_in", [float(v) for v in tin]), ("tokens_out", [float(v) for v in tout])], th["value"], "tokens", minutes, bars=True)
        + legend(["tokens_in", "tokens_out"]),
    )
    # 6. quality
    q = [r["quality_score"] for r in all_sent]
    qavg = sum(q) / len(q) if q else 0.0
    th = panels["quality"]["threshold"]
    qm = [(sum(r["quality_score"] for r in b) / len(b) if b else None) for b in sent]
    card(
        "quality",
        stat("mean quality", f"{qavg:.3f}", check(qavg, th)),
        chart([("quality", qm)], th["value"], "score", minutes) + legend(["mean quality score"]),
    )

    stamp = f"{start:%H:%M}–{end:%H:%M} UTC"
    title = html.escape(cfg["title"])
    doc = (
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{CSS}</style></head><body><h1>{title}</h1>"
        f'<div class="meta">Time range: last {minutes} min ({stamp}) · refresh {cfg["refresh_seconds"]}s · '
        f"source: data/logs.jsonl · {len(all_sent)} responses, {all_recv} requests</div>"
        f'<div class="board">{"".join(cards)}</div>'
        f'<script>setTimeout(()=>location.reload(),{cfg["refresh_seconds"] * 1000})</script></body></html>'
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(doc, encoding="utf-8")
    print(f"Dashboard: {a.out}  ({stamp}, {len(all_sent)} responses, {all_recv} requests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
