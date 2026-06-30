"""Palette et helpers UI partagés entre les pages Streamlit."""

BG = "#0d1117"
BG_CARD = "#161b22"
BG_CARD2 = "#1c2230"
BORDER = "#30363d"
ACCENT = "#58a6ff"
GREEN = "#3fb950"
RED = "#f85149"
YELLOW = "#d29922"
TEXT = "#e6edf3"
MUTED = "#8b949e"
PURPLE = "#bc8cff"

CHART_C = [
    "#58a6ff", "#3fb950", "#f78166", "#d29922",
    "#bc8cff", "#39d353", "#ff7b72", "#ffa657",
]


def rgba(hex_color: str, alpha: float = 0.15) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return hex_color
