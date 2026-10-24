#!/usr/bin/env python3
"""Write the FastAPI OpenAPI document to openapi.json."""

import json
from pathlib import Path

from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    app = create_app()
    spec = app.openapi()
    (ROOT / "openapi.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {ROOT / 'openapi.json'}: {len(spec['paths'])} paths")


if __name__ == "__main__":
    main()
