"""Build the standalone article page: inline the SVG figures into the
template so writeup/index.html is a single self-contained file.

Usage: python scripts/build_writeup.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "writeup" / "template.html"
OUT = ROOT / "writeup" / "index.html"
FIGURES = ROOT / "figures"


def inline_svg(name: str) -> str:
    svg = (FIGURES / f"{name}.svg").read_text()
    svg = svg[svg.index("<svg"):]  # strip XML/DOCTYPE prologue
    # responsive: let CSS drive the size, keep the aspect via viewBox
    svg = re.sub(r'(<svg[^>]*?) width="[^"]*" height="[^"]*"', r"\1", svg, count=1)
    return f'{svg}'


def main() -> None:
    html = TEMPLATE.read_text()
    html = re.sub(
        r"\{\{SVG:(\w+)\}\}", lambda m: inline_svg(m.group(1)), html
    )
    OUT.write_text(html)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
