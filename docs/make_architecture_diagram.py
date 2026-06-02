"""Generate docs/architecture.svg -- the system architecture diagram.

Run from the mvp/ folder:  python docs/make_architecture_diagram.py
Self-contained (standard library only). Edit the STEPS list and re-run to
regenerate the SVG; keeps the diagram in sync with the agentic loop.
"""
from pathlib import Path

W = 980

PALETTE = {
    "agent":  ("#ede9fe", "#7c3aed"),  # purple  -- LLM / orchestration
    "llm":    ("#ede9fe", "#7c3aed"),
    "google": ("#dbeafe", "#2563eb"),  # blue    -- Google APIs
    "data":   ("#dcfce7", "#16a34a"),  # green   -- data / ML / Python
    "input":  ("#f1f5f9", "#475569"),  # slate   -- user inputs
    "output": ("#ffedd5", "#ea580c"),  # orange  -- final deliverable
}

INPUTS = [
    ("Target date", "+ how many carts"),
    ("OpenAI API key", "Responses + web search"),
    ("Google Maps key", "geocode / places / routes / map"),
]

# (number, title, one-line description, tool/api label, palette key)
STEPS = [
    ("1", "Web Search", "Search the live web for events on the target date",
     "OpenAI web_search_preview", "llm"),
    ("2", "Extract & Parse", "Geocode venues, fetch weather, tag event types",
     "Google Geocoding API  +  Open-Meteo", "google"),
    ("3", "Foot-Traffic Model", "Predict pedestrian volume for each of 14 zones",
     "sklearn LinearRegression", "data"),
    ("4", "RAG  --  Internal Data", "Retrieve cart fleet, inventory, micro-spots",
     "carts.json  +  zone_spots.json", "data"),
    ("5", "Foot-Traffic Map", "Render the predicted-density heat-map",
     "Google Maps JS  +  deck.gl", "google"),
    ("6", "Non-Linear Optimizer", "Maximize revenue (cannibalization-aware)",
     "custom Python brute-force NLP", "data"),
]

OUTPUT = ("7", "Placement Plan  --  Streamlit UI",
          "KPI band   .   placement table   .   interactive map   .   per-cart reasoning")


def rrect(x, y, w, h, fill, stroke, rx=10, sw=2):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, weight="normal", fill="#0f172a", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="HEIGHT" '
    f'viewBox="0 0 {W} HEIGHT" font-family="Segoe UI, Arial, sans-serif">',
    '<defs>',
    '<marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" '
    'orient="auto" markerUnits="strokeWidth">'
    '<path d="M0,0 L7,3 L0,6 z" fill="#475569"/></marker>',
    '<marker id="loop" markerWidth="10" markerHeight="10" refX="7" refY="3" '
    'orient="auto" markerUnits="strokeWidth">'
    '<path d="M0,0 L7,3 L0,6 z" fill="#7c3aed"/></marker>',
    '</defs>',
    f'<rect x="0" y="0" width="{W}" height="HEIGHT" fill="#ffffff"/>',
]

# ---- title ----
parts.append(text(W / 2, 40, "Agentic Drink Cart Placement Optimizer",
                  size=24, weight="700", anchor="middle"))
parts.append(text(W / 2, 64, "System architecture: a 7-step autonomous agent loop",
                  size=14, fill="#64748b", anchor="middle"))

# ---- inputs band ----
iy = 92
iw, igap = 290, 20
ix0 = (W - (iw * 3 + igap * 2)) / 2
f, s = PALETTE["input"]
for i, (a, b) in enumerate(INPUTS):
    x = ix0 + i * (iw + igap)
    parts.append(rrect(x, iy, iw, 52, f, s, rx=8))
    parts.append(text(x + iw / 2, iy + 22, a, size=14, weight="600", anchor="middle"))
    parts.append(text(x + iw / 2, iy + 40, b, size=12, fill="#64748b", anchor="middle"))
parts.append(text(ix0, iy - 8, "USER INPUT  (sidebar)", size=11, weight="700", fill="#94a3b8"))

# ---- agent banner ----
ay = 168
f, s = PALETTE["agent"]
parts.append(rrect(60, ay, W - 120, 60, f, s, rx=12))
parts.append(text(W / 2, ay + 26, "AGENTIC LOOP  --  OpenAI Responses API  (gpt-4o-mini)",
                  size=16, weight="700", fill="#5b21b6", anchor="middle"))
parts.append(text(W / 2, ay + 46,
                  "autonomously selects which tools to call, iterates when data is incomplete, "
                  "and self-corrects via a runtime validator",
                  size=12, fill="#6d28d9", anchor="middle"))
# arrow inputs -> agent
parts.append(f'<line x1="{W/2}" y1="{iy+52}" x2="{W/2}" y2="{ay}" '
             f'stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>')

# ---- steps ----
step_x, step_w, step_h = 90, 470, 70
tool_x, tool_w = 600, 300
gap = 26
y = ay + 92
centers = []
for num, title_, desc, tool, key in STEPS:
    f, s = PALETTE[key]
    # process box
    parts.append(rrect(step_x, y, step_w, step_h, "#ffffff", "#cbd5e1", rx=10))
    # number circle
    cf, cs = PALETTE[key]
    parts.append(f'<circle cx="{step_x+30}" cy="{y+step_h/2}" r="17" fill="{cf}" stroke="{cs}" stroke-width="2"/>')
    parts.append(text(step_x + 30, y + step_h / 2 + 5, num, size=16, weight="700", fill=cs, anchor="middle"))
    parts.append(text(step_x + 60, y + 30, title_, size=16, weight="700"))
    parts.append(text(step_x + 60, y + 52, desc, size=13, fill="#475569"))
    # tool pill
    parts.append(rrect(tool_x, y + 13, tool_w, step_h - 26, f, s, rx=20))
    parts.append(text(tool_x + tool_w / 2, y + step_h / 2 + 5, tool, size=13, weight="600", fill=s, anchor="middle"))
    # arrow step -> tool
    parts.append(f'<line x1="{step_x+step_w}" y1="{y+step_h/2}" x2="{tool_x}" y2="{y+step_h/2}" '
                 f'stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>')
    centers.append((step_x + step_w / 2, y, y + step_h))
    y += step_h + gap

# down-arrows between steps
for i in range(len(centers) - 1):
    cx, _, bottom = centers[i]
    _, top_next, _ = centers[i + 1]
    parts.append(f'<line x1="{cx}" y1="{bottom}" x2="{cx}" y2="{top_next}" '
                 f'stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>')

# arrow agent -> step 1
parts.append(f'<line x1="{centers[0][0]}" y1="{ay+60}" x2="{centers[0][0]}" y2="{centers[0][1]}" '
             f'stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>')

# ---- output box ----
oy = y + 6
f, s = PALETTE["output"]
parts.append(rrect(step_x, oy, W - 2 * step_x, 76, f, s, rx=12))
parts.append(f'<circle cx="{step_x+34}" cy="{oy+38}" r="18" fill="#ffffff" stroke="{s}" stroke-width="2"/>')
parts.append(text(step_x + 34, oy + 43, OUTPUT[0], size=16, weight="700", fill=s, anchor="middle"))
parts.append(text(step_x + 66, oy + 32, OUTPUT[1], size=16, weight="700", fill="#9a3412"))
parts.append(text(step_x + 66, oy + 54, OUTPUT[2], size=13, fill="#9a3412"))
parts.append(f'<line x1="{centers[-1][0]}" y1="{centers[-1][2]}" x2="{centers[-1][0]}" y2="{oy}" '
             f'stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>')

# ---- loop-back arrow (output -> agent) ----
lx = 40
parts.append(
    f'<path d="M {step_x} {oy+38} L {lx} {oy+38} L {lx} {ay+30} L 60 {ay+30}" '
    f'fill="none" stroke="#7c3aed" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#loop)"/>'
)
parts.append(f'<text x="{lx-6}" y="{(ay+oy)/2}" font-family="Segoe UI, Arial, sans-serif" '
             f'font-size="12" font-weight="600" fill="#7c3aed" text-anchor="middle" '
             f'transform="rotate(-90 {lx-6} {(ay+oy)/2})">agent re-runs the loop / validator forces a retry</text>')

# ---- legend ----
ly = oy + 100
legend = [("LLM / orchestration", "agent"), ("Google APIs", "google"),
          ("Data / ML / Python", "data"), ("User input", "input"), ("Deliverable", "output")]
lx0 = step_x
parts.append(text(lx0, ly, "Legend:", size=12, weight="700", fill="#64748b"))
cx = lx0 + 64
for label, key in legend:
    f, s = PALETTE[key]
    parts.append(rrect(cx, ly - 12, 16, 16, f, s, rx=4, sw=1.5))
    parts.append(text(cx + 22, ly, label, size=12, fill="#475569"))
    cx += 30 + len(label) * 7 + 24

H = ly + 30
svg = "\n".join(parts).replace("HEIGHT", str(int(H))) + "\n</svg>\n"

out = Path(__file__).with_name("architecture.svg")
out.write_text(svg, encoding="utf-8")
print(f"Wrote {out}  ({int(H)}px tall)")
