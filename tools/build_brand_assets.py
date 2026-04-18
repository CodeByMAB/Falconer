#!/usr/bin/env python3
"""Generate README banner SVG and PNG brand assets from the dashboard favicon SVG.

Requires ``rsvg-convert`` (librsvg) for PNG export; install on macOS: brew install librsvg
"""
from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAVICON_SVG = REPO / "src/falconer/dashboard/static/favicon.svg"
ASSETS = REPO / "assets"
BANNER_W, BANNER_H = 1280, 360


def _read_favicon_inner() -> str:
    text = FAVICON_SVG.read_text(encoding="utf-8")
    i = text.index("<rect")
    j = text.rindex("</svg>")
    return text[i:j].strip()


def _stars_layer() -> str:
    random.seed(42)
    parts: list[str] = []
    for _ in range(200):
        x = random.random() * BANNER_W
        y = random.random() * BANNER_H * 0.72
        r = random.uniform(0.2, 1.6)
        roll = random.random()
        if roll < 0.78:
            fill, op = "#e8edf5", random.uniform(0.1, 0.82)
        elif roll < 0.93:
            fill, op = "#f5a623", random.uniform(0.06, 0.42)
        else:
            fill, op = "#3aa5f5", random.uniform(0.06, 0.32)
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" opacity="{op:.3f}"/>'
        )
    for _ in range(22):
        x = random.random() * BANNER_W
        y = random.random() * BANNER_H * 0.58
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.1" fill="#fff8e8" opacity="0.92"/>'
        )
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#f5a623" opacity="0.14"/>'
        )
    return "\n    ".join(parts)


def build_banner_svg() -> str:
    inner = _read_favicon_inner()
    stars = _stars_layer()
    mountains = (
        "M0,360 L0,300 L120,265 L220,285 L340,240 L460,270 L560,250 L680,290 "
        "L800,255 L920,275 L1040,245 L1160,268 L1280,252 L1280,360 Z"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{BANNER_W}" height="{BANNER_H}" viewBox="0 0 {BANNER_W} {BANNER_H}" role="img" aria-label="Falconer banner">
  <defs>
    <linearGradient id="banner-sky" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#04080f"/>
      <stop offset="50%" stop-color="#0a1525"/>
      <stop offset="100%" stop-color="#0d2035"/>
    </linearGradient>
    <linearGradient id="banner-glow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f5a623" stop-opacity="0"/>
      <stop offset="40%" stop-color="#f5a623" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#f5a623" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#banner-sky)"/>
  <rect width="100%" height="100%" fill="url(#banner-glow)" opacity="0.9"/>
  <g aria-hidden="true">
    {stars}
  </g>
  <path d="{mountains}" fill="#050c18" opacity="0.88"/>
  <path d="{mountains}" fill="none" stroke="#f5a623" stroke-opacity="0.08" stroke-width="1"/>
  <svg x="36" y="52" width="228" height="228" viewBox="0 8 240 240">
    {inner}
  </svg>
  <g font-family="system-ui, -apple-system, Segoe UI, Helvetica Neue, Arial, sans-serif">
    <text x="296" y="158" font-size="64" font-weight="700" fill="#f5a623" letter-spacing="0.14em">FALCONER</text>
    <text x="298" y="204" font-size="21" font-weight="500" fill="#7a8fa6" letter-spacing="0.18em">BITCOIN-NATIVE AI AGENT</text>
    <line x1="296" y1="224" x2="1180" y2="224" stroke="#f5a623" stroke-opacity="0.28" stroke-width="1"/>
    <text x="298" y="254" font-size="15" font-weight="400" fill="#3a5070" letter-spacing="0.1em">COMMAND INTERFACE</text>
  </g>
</svg>
"""


def run_rsvg(svg_path: Path, png_path: Path, width: int | None) -> None:
    cmd = ["rsvg-convert", "-o", str(png_path)]
    if width is not None:
        cmd.extend(["-w", str(width)])
    cmd.append(str(svg_path))
    subprocess.run(cmd, check=True)


def main() -> int:
    if not FAVICON_SVG.is_file():
        print("Missing favicon SVG:", FAVICON_SVG, file=sys.stderr)
        return 1
    ASSETS.mkdir(parents=True, exist_ok=True)

    banner_svg = ASSETS / "falconer-banner.svg"
    banner_svg.write_text(build_banner_svg(), encoding="utf-8")
    print("Wrote", banner_svg)

    try:
        run_rsvg(FAVICON_SVG, ASSETS / "falconer-icon.png", 256)
        print("Wrote", ASSETS / "falconer-icon.png", "(256×256)")
        run_rsvg(FAVICON_SVG, ASSETS / "falconer-icon-512.png", 512)
        print("Wrote", ASSETS / "falconer-icon-512.png")
        run_rsvg(banner_svg, ASSETS / "falconer-banner.png", 1280)
        print("Wrote", ASSETS / "falconer-banner.png")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(
            "PNG export skipped or failed (install librsvg / rsvg-convert):",
            e,
            file=sys.stderr,
        )
        print("SVG sources are still in assets/ — run rsvg-convert manually.", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
