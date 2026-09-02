"""Central design tokens for Seat Watcher's presentation layer."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Theme:
    canvas: str = "#02030A"
    shell: str = "#080B13"
    surface: str = "#111727"
    raised: str = "#1C2437"
    field: str = "#070B13"
    border: str = "#303B55"
    border_hi: str = "#53617D"
    text: str = "#FCFCFF"
    soft: str = "#DCE3F1"
    dim: str = "#96A2B9"
    purple: str = "#C44DFF"
    purple_hover: str = "#D878FF"
    cyan: str = "#16D9FF"
    cyan_hover: str = "#55E5FF"
    green: str = "#32F0A1"

THEME = Theme()
