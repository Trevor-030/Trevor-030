"""Generate the animated SVGs in assets/ for the profile README.

Text is drawn as outlines from Bricolage Grotesque, so the SVGs look the
same everywhere and need no web fonts. Run from the repo root:

    pip install fonttools
    python scripts/build_assets.py

The font is downloaded to scripts/.cache/ on first run.
"""

from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CACHE = Path(__file__).resolve().parent / ".cache"
FONT_URL = (
    "https://github.com/google/fonts/raw/main/ofl/bricolagegrotesque/"
    "BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf"
)

# Palette: kente cloth and the Ghana flag on a deep forest ground.
FOREST = "#0D2B20"
FOREST_2 = "#133829"
GOLD = "#F2B33D"
RED = "#CE3B2B"
LEAF = "#3FA36B"
COTTON = "#F5ECD7"
SAGE = "#A9BFB2"
THREAD_BLACK = "#1A1410"


# ---------------------------------------------------------------- type
class Face:
    def __init__(self, font: TTFont, key: str):
        self.key = key
        self.used: set[str] = set()
        self.font = font
        self.upm = font["head"].unitsPerEm
        self.cmap = font.getBestCmap()
        self.glyphs = font.getGlyphSet()
        self.hmtx = font["hmtx"]
        self._paths: dict[str, str] = {}

    def _path(self, name: str) -> str:
        if name not in self._paths:
            pen = SVGPathPen(self.glyphs)
            self.glyphs[name].draw(pen)
            self._paths[name] = pen.getCommands()
        return self._paths[name]

    def width(self, text: str, size: float, tracking: float = 0) -> float:
        units = sum(self.hmtx[self.cmap[ord(c)]][0] for c in text)
        return units * size / self.upm + tracking * size * (len(text) - 1)

    def draw(self, text, x, y, size, fill, tracking=0.0, cls="", anchor="start"):
        """Return a <g> holding the text as outlines with its baseline at y."""
        if anchor == "middle":
            x -= self.width(text, size, tracking) / 2
        scale = size / self.upm
        track_units = tracking * self.upm
        parts, cursor = [], 0.0
        for ch in text:
            name = self.cmap[ord(ch)]
            if self._path(name):
                self.used.add(name)
                parts.append(f'<use xlink:href="#{self.key}-{name}" x="{cursor:.0f}"/>')
            cursor += self.hmtx[name][0] + track_units
        cls_attr = f' class="{cls}"' if cls else ""
        return (
            f'<g{cls_attr} fill="{fill}" transform="translate({x:.1f} {y:.1f}) '
            f'scale({scale:.5f} {-scale:.5f})">{"".join(parts)}</g>'
        )


def load_faces() -> dict[str, Face]:
    CACHE.mkdir(exist_ok=True)
    src = CACHE / "BricolageGrotesque.ttf"
    if not src.exists():
        urllib.request.urlretrieve(FONT_URL, src)
    settings = {
        "display": {"wght": 800, "opsz": 96, "wdth": 100},
        "sub": {"wght": 600, "opsz": 28, "wdth": 100},
        "body": {"wght": 400, "opsz": 14, "wdth": 100},
    }
    return {
        key: Face(instancer.instantiateVariableFont(TTFont(src), axes), key)
        for key, axes in settings.items()
    }


# ---------------------------------------------------------------- kente
def kente_column(w: float, seed: int) -> tuple[list[str], float]:
    """One woven strip, drawn top-down from y=0. Returns (elements, height)."""
    rng = random.Random(seed)
    out: list[str] = []
    y = 0.0
    kinds = ["bands", "warp", "check", "diamond", "bands", "warp"]
    rng.shuffle(kinds)
    for kind in kinds * 2:
        h = rng.choice([28, 34, 40, 46])
        if kind == "bands":
            colors = rng.choice([
                [GOLD, THREAD_BLACK, GOLD, RED, GOLD],
                [LEAF, GOLD, THREAD_BLACK, GOLD, LEAF],
                [RED, GOLD, LEAF, GOLD, RED],
            ])
            bh = h / len(colors)
            for i, c in enumerate(colors):
                out.append(f'<rect y="{y + i * bh:.1f}" width="{w}" height="{bh + 0.3:.1f}" fill="{c}"/>')
        elif kind == "warp":
            colors = rng.choice([[GOLD, LEAF], [GOLD, THREAD_BLACK], [RED, GOLD]])
            out.append(f'<rect y="{y:.1f}" width="{w}" height="{h}" fill="{colors[0]}"/>')
            step = w / 8
            for i in range(1, 8, 2):
                out.append(f'<rect x="{i * step:.1f}" y="{y:.1f}" width="{step:.1f}" height="{h}" fill="{colors[1]}"/>')
        elif kind == "check":
            a, b = rng.choice([(GOLD, THREAD_BLACK), (GOLD, RED), (LEAF, GOLD)])
            cell = w / 5
            rows = max(2, round(h / cell))
            cell_h = h / rows
            out.append(f'<rect y="{y:.1f}" width="{w}" height="{h}" fill="{a}"/>')
            for r in range(rows):
                for c in range(5):
                    if (r + c) % 2:
                        out.append(
                            f'<rect x="{c * cell:.1f}" y="{y + r * cell_h:.1f}" '
                            f'width="{cell:.1f}" height="{cell_h:.1f}" fill="{b}"/>'
                        )
        else:  # diamond motif on a gold ground
            ground, mark = rng.choice([(GOLD, THREAD_BLACK), (THREAD_BLACK, GOLD), (RED, GOLD)])
            out.append(f'<rect y="{y:.1f}" width="{w}" height="{h}" fill="{ground}"/>')
            cx, cy = w / 2, y + h / 2
            dx, dy = w * 0.32, h * 0.38
            out.append(
                f'<path d="M{cx:.1f} {cy - dy:.1f}L{cx + dx:.1f} {cy:.1f}L{cx:.1f} {cy + dy:.1f}'
                f'L{cx - dx:.1f} {cy:.1f}Z" fill="{mark}"/>'
            )
        y += h
    return out, y


def kente_loop(w: float, seed: int, min_height: float) -> tuple[str, float]:
    """A strip repeated enough times to cover min_height plus one period."""
    elems, period = kente_column(w, seed)
    tile_id = f"tile{seed}"
    if not any(f'id="{tile_id}"' in d for d in DEFS):
        DEFS.append(f'<g id="{tile_id}">{"".join(elems)}</g>')
    copies = int((min_height // period) + 2)
    tiles = "".join(
        f'<use xlink:href="#{tile_id}" y="{i * period:.1f}"/>' for i in range(copies)
    )
    return tiles, period


DEFS: list[str] = []
FACES: list[Face] = []


def take_defs() -> str:
    """Shared shapes used by the document being built, then reset."""
    out = list(DEFS)
    for face in FACES:
        out += [f'<path id="{face.key}-{n}" d="{face._path(n)}"/>' for n in sorted(face.used)]
        face.used.clear()
    DEFS.clear()
    return f"<defs>{''.join(out)}</defs>"


REDUCED = (
    "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
)


def svg(width, height, title, desc, style, body) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">'
        f'<title id="t">{title}</title><desc id="d">{desc}</desc>'
        f"<style>{style}{REDUCED}</style>{take_defs()}{body}</svg>\n"
    )


# ---------------------------------------------------------------- hero
def hero(f: dict[str, Face]) -> str:
    W, H = 1200, 420
    loom_x, strip_w, strips = 900, 50, 6
    style = [
        ".rise{animation:rise 1s cubic-bezier(.2,.8,.2,1) both}",
        "@keyframes rise{from{transform:translateY(110px)}}",
        ".fade{animation:fade .9s ease-out both}",
        "@keyframes fade{from{opacity:0;transform:translateY(10px)}}",
        ".cover{animation:weave 1.7s cubic-bezier(.65,0,.35,1) both}",
        "@keyframes weave{to{transform:translateY(440px)}}",
        ".word{opacity:0;animation:word 10s ease-in-out infinite both}",
        "@keyframes word{0%{opacity:0;transform:translateY(16px)}"
        "4%,22%{opacity:1;transform:none}"
        "26%,100%{opacity:0;transform:translateY(-16px)}}",
    ]
    body = [
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>',
        '<g clip-path="url(#card)">',
        f'<rect width="{W}" height="{H}" fill="{FOREST}"/>',
    ]

    # The loom: six strips that weave in, then drift up and down forever.
    for i in range(strips):
        x = loom_x + i * strip_w
        tiles, period = kente_loop(strip_w, seed=30 + i, min_height=H)
        # neighbouring strips drift in opposite directions
        a, b = (0, -period) if i % 2 == 0 else (-period, 0)
        dur = 38 + i * 5
        style.append(
            f".s{i}{{animation:s{i} {dur}s linear infinite}}"
            f"@keyframes s{i}{{from{{transform:translateY({a:.1f}px)}}"
            f"to{{transform:translateY({b:.1f}px)}}}}"
        )
        body.append(f'<g transform="translate({x} 0)"><g class="s{i}">{tiles}</g></g>')
    for i in range(strips):
        x = loom_x + i * strip_w
        body.append(
            f'<rect class="cover" style="animation-delay:{0.15 + i * 0.12:.2f}s" '
            f'x="{x}" y="0" width="{strip_w}" height="{H}" fill="{FOREST}"/>'
        )
    # seams between strips, like the hand-sewn joins of a kente cloth
    for i in range(1, strips):
        x = loom_x + i * strip_w
        body.append(f'<rect x="{x - 0.75}" width="1.5" height="{H}" fill="{FOREST}" opacity=".55"/>')

    # Words
    left = 64
    body.append(f'<g class="fade" style="animation-delay:.2s">{f["sub"].draw("Akwaaba, I’m", left, 100, 26, GOLD)}</g>')
    name_size = 84
    for line, (text, base) in enumerate([("Michael Agyenim", 186), ("Boateng Anning", 270)]):
        body.append(
            f'<clipPath id="ln{line}"><rect x="0" y="{base - 90}" width="880" height="112"/></clipPath>'
            f'<g clip-path="url(#ln{line})"><g class="rise" style="animation-delay:{0.35 + line * 0.14:.2f}s">'
            f'{f["display"].draw(text, left, base, name_size, COTTON, tracking=-0.025)}</g></g>'
        )

    lead = "I build "
    lead_w = f["sub"].width(lead, 30)
    body.append(f'<g class="fade" style="animation-delay:1.1s">{f["sub"].draw(lead, left, 340, 30, COTTON)}</g>')
    words = ["web apps.", "mobile apps.", "real-time systems.", "AI-powered tools."]
    for i, w in enumerate(words):
        body.append(
            f'<g class="word" style="animation-delay:{1.3 + i * 2.5:.1f}s">'
            f'{f["sub"].draw(w, left + lead_w, 340, 30, GOLD)}</g>'
        )
    body.append(
        f'<g class="fade" style="animation-delay:1.5s">'
        f'{f["body"].draw("Computer Science & Engineering student at UMaT in Tarkwa, Ghana", left, 382, 17, SAGE)}</g>'
    )
    body.append("</g>")
    return svg(
        W, H,
        "Michael Agyenim Boateng Anning, full-stack developer",
        "Akwaaba, I'm Michael Agyenim Boateng Anning. I build web apps, mobile apps, "
        "real-time systems and AI-powered tools. Beside the name, strips of kente cloth weave in.",
        "".join(style), "".join(body),
    )


# ---------------------------------------------------------------- divider
def horizontal_band(width, height, seed, dur, y=0) -> tuple[str, str]:
    """A kente strip laid on its side, scrolling left. Returns (style, body)."""
    tiles, period = kente_loop(height, seed=seed, min_height=width)
    style = (
        f".h{seed}{{animation:h{seed} {dur}s linear infinite}}"
        f"@keyframes h{seed}{{to{{transform:translateX(-{period:.1f}px)}}}}"
    )
    # rotate the vertical strip so it runs left to right
    body = (
        f'<g transform="translate(0 {y})"><g class="h{seed}">'
        f'<g transform="translate(0 {height}) rotate(-90)">{tiles}</g></g></g>'
    )
    return style, body


def divider() -> str:
    W, H = 1200, 20
    style, band = horizontal_band(W, 8, seed=7, dur=50, y=6)
    body = (
        '<defs><linearGradient id="fadeEdge"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".2" stop-color="#fff"/><stop offset=".8" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fadeEdge)"/></mask></defs>'
        f'<g mask="url(#m)">{band}</g>'
    )
    return svg(W, H, "Divider", "A thin strip of kente cloth drifting sideways.", style, body)


# ---------------------------------------------------------------- now building
def project_row(f, name, blurb, stack, action, seed) -> str:
    W, H = 1200, 150
    tiles, period = kente_loop(16, seed=seed, min_height=H)
    style = (
        f".k{{animation:k 30s linear infinite}}@keyframes k{{to{{transform:translateY(-{period:.1f}px)}}}}"
        ".cover{animation:weave 1.3s cubic-bezier(.65,0,.35,1) .1s both}"
        "@keyframes weave{to{transform:translateY(160px)}}"
        ".fade{animation:fade .8s ease-out both}"
        "@keyframes fade{from{opacity:0;transform:translateX(-12px)}}"
        ".thread{stroke-dasharray:14 10;animation:run 1.6s linear infinite}"
        "@keyframes run{to{stroke-dashoffset:-24}}"
    )
    action_w = f["sub"].width(action, 17)
    body = (
        f'<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
        f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{FOREST}"/>'
        f'<g class="k">{tiles}</g>'
        f'<rect class="cover" width="16" height="{H}" fill="{FOREST}"/>'
        f'<g class="fade" style="animation-delay:.25s">{f["display"].draw(name, 52, 62, 38, COTTON, tracking=-0.02)}</g>'
        f'<g class="fade" style="animation-delay:.4s">{f["body"].draw(blurb, 52, 96, 19, COTTON)}</g>'
        f'<g class="fade" style="animation-delay:.55s">{f["body"].draw(stack, 52, 126, 15, SAGE)}</g>'
        # a thread running through, to show the work is still on the loom
        f'<line class="thread" x1="880" y1="74" x2="1140" y2="74" stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="880" y1="74" x2="1140" y2="74" stroke="{RED}" stroke-width="3" opacity=".35"/>'
        f'{f["sub"].draw(action, 1140 - action_w, 110, 17, GOLD)}'
        "</g>"
    )
    return svg(W, H, name, f"{name}: {blurb} Built with {stack}.", style, body)


# ---------------------------------------------------------------- footer
def footer(f) -> str:
    W, H = 1200, 220
    style_band, band = horizontal_band(W, 16, seed=11, dur=60, y=0)
    style = style_band + (
        ".fade{animation:fade 1s ease-out both}"
        "@keyframes fade{from{opacity:0;transform:translateY(12px)}}"
    )
    body = (
        f'<clipPath id="c"><rect width="{W}" height="{H}" rx="22"/></clipPath>'
        f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{FOREST}"/>{band}'
        f'<g class="fade" style="animation-delay:.2s">'
        f'{f["display"].draw("Medaase for stopping by.", W / 2, 122, 54, COTTON, tracking=-0.02, anchor="middle")}</g>'
        f'<g class="fade" style="animation-delay:.45s">'
        f'{f["sub"].draw("Build. Ship. Learn. Repeat.", W / 2, 172, 22, GOLD, anchor="middle")}</g>'
        "</g>"
    )
    return svg(
        W, H, "Medaase for stopping by",
        "Medaase means thank you in Twi. Build. Ship. Learn. Repeat.",
        style, body,
    )


PROJECTS = [
    ("aucourant", "AuCourant",
     "Turns MTN and Telecel Mobile Money texts into a searchable ledger.",
     "Android, Expo, React Native, Java", "Open on GitHub", 41),
    ("lodgenest", "LodgeNest",
     "Helps students in Ghana find and compare hostels on a live map.",
     "Expo, React Native, Supabase", "Visit the site", 52),
    ("yt-cli", "YouTube Downloader CLI",
     "Saves playlists, channels and transcripts from the terminal.",
     "Python, yt-dlp", "Open on GitHub", 63),
]


def main() -> None:
    faces = load_faces()
    FACES.extend(faces.values())
    ASSETS.mkdir(exist_ok=True)
    out = {
        "profile-hero.svg": hero(faces),
        "divider.svg": divider(),
        "footer.svg": footer(faces),
    }
    for slug, name, blurb, stack, action, seed in PROJECTS:
        out[f"now-{slug}.svg"] = project_row(faces, name, blurb, stack, action, seed)
    for file, text in out.items():
        (ASSETS / file).write_text(text, encoding="utf-8")
        print(f"{file}: {len(text) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
