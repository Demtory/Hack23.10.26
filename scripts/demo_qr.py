#!/usr/bin/env python3
"""Перевыпуск QR-кода для входа на демо-стенд без пароля.

    DEMO_LOGIN_TOKEN=... python scripts/demo_qr.py \
        --base http://193.233.246.179:8000 \
        --out pitch/qr-demo.png

Токен берётся из аргумента --token или переменной DEMO_LOGIN_TOKEN.
Ссылка ведёт на /api/v1/auth/demo, который ставит сессию и редиректит в панель.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlencode

try:
    import qrcode
except ImportError:  # pragma: no cover - подсказка вместо трейсбека
    raise SystemExit("Нужен пакет qrcode: pip install qrcode pillow")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://193.233.246.179:8000")
    parser.add_argument("--token", default=os.getenv("DEMO_LOGIN_TOKEN", ""))
    parser.add_argument("--out", default="pitch/qr-demo.png")
    args = parser.parse_args()
    if not args.token:
        raise SystemExit("Не задан токен: --token или DEMO_LOGIN_TOKEN")

    url = f"{args.base.rstrip('/')}/api/v1/auth/demo?{urlencode({'token': args.token})}"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#182d48", back_color="white")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    print(f"QR сохранён: {out}\nСсылка: {url}")


if __name__ == "__main__":
    main()
