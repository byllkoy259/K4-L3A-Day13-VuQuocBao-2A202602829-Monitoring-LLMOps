"""Tạo prompt v1/v2 trên Langfuse cá nhân và đổi label `production` (promote/rollback)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

from langfuse import get_client  # noqa: E402

V1 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
V2 = (
    "You are a concise assistant. Answer in at most three sentences.\n"
    "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
)


def _name() -> str:
    return os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")


def create(client) -> None:
    name = _name()
    v1 = client.create_prompt(name=name, type="text", prompt=V1, labels=["baseline", "production"])
    v2 = client.create_prompt(name=name, type="text", prompt=V2, labels=["candidate"])
    print(f"created {name} v{v1.version} (baseline, production) and v{v2.version} (candidate)")


def promote(client, version: int) -> None:
    name = _name()
    client.update_prompt(name=name, version=version, new_labels=["production"])
    print(f"label production -> {name} v{version}")


def show(client) -> None:
    name = _name()
    for label in ("baseline", "candidate", "production"):
        p = client.get_prompt(name, label=label, type="text", cache_ttl_seconds=0)
        print(f"{label:<10} -> v{p.version}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create", help="tạo v1 (baseline, production) và v2 (candidate)")
    pr = sub.add_parser("promote", help="đặt label production cho một version (dùng cả để rollback)")
    pr.add_argument("version", type=int)
    sub.add_parser("show", help="in version đang gắn với từng label")
    args = parser.parse_args()

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        print("Thiếu LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY trong .env")
        return 1
    client = get_client()
    {"create": lambda: create(client), "promote": lambda: promote(client, args.version), "show": lambda: show(client)}[args.cmd]()
    client.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
