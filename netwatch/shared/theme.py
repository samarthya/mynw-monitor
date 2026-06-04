CATEGORY_COLORS: dict[str, str] = {
    "productive": "#1D9E75",
    "distracting": "#D85A30",
    "background": "#888780",
    "system": "#378ADD",
    "unknown": "#B4B2A9",
}

CHART_PALETTE: list[str] = ["#1D9E75", "#378ADD", "#7F77DD", "#D85A30", "#EF9F27"]

FONT_FAMILY: str = "Inter, system-ui, sans-serif"
FONT_SIZE_BASE: int = 14

GLOBAL_CSS: str = """
<style>
  [data-testid="stAppViewContainer"] { font-family: Inter, system-ui, sans-serif; }
  .metric-card { background: #f8f8f6; border-radius: 10px; padding: 1rem; }
  .badge-productive { background:#E1F5EE; color:#0F6E56; border-radius:6px; padding:2px 8px; font-size:12px; }
  .badge-distracting { background:#FAECE7; color:#993C1D; border-radius:6px; padding:2px 8px; font-size:12px; }
  .badge-background  { background:#F1EFE8; color:#5F5E5A; border-radius:6px; padding:2px 8px; font-size:12px; }
  .badge-system      { background:#E6F1FB; color:#185FA5; border-radius:6px; padding:2px 8px; font-size:12px; }
  .badge-unknown     { background:#F1EFE8; color:#888780; border-radius:6px; padding:2px 8px; font-size:12px; }
</style>
"""
