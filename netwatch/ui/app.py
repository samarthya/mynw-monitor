from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from netwatch.analytics.engine import (
    get_hourly_breakdown,
    get_productivity_score,
    get_top_domains,
    get_weekly_trend,
)
from netwatch.shared.config import Settings
from netwatch.shared.theme import CATEGORY_COLORS, CHART_PALETTE, GLOBAL_CSS


def run_app() -> None:
    st.set_page_config(page_title="NetWatch", layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    settings = Settings.load()
    if settings.theme.lower() == "dark":
        st.markdown(
            """
            <style>
              [data-testid="stAppViewContainer"] { background-color: #111827; color: #F9FAFB; }
              [data-testid="stSidebar"] { background-color: #0F172A; color: #F9FAFB; }
              .metric-card { background: #1F2937; }
            </style>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.title("NetWatch")
    page = st.sidebar.radio("Page", ["Today", "History", "Rules", "Settings"])

    if page == "Today":
        _render_today(settings)
    elif page == "History":
        _render_history(settings)
    elif page == "Rules":
        _render_rules(settings)
    else:
        _render_settings(settings)



def _render_today(settings: Settings) -> None:
    st.header("Today")
    today = date.today()
    score = get_productivity_score(today, db_path=settings.resolved_db_path())

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Productivity Score", f"{score.score:.1f}%")
        st.caption(
            f"Productive: {score.productive_seconds}s | "
            f"Distracting: {score.distracting_seconds}s | "
            f"Unknown: {score.unknown_seconds}s"
        )

    with col2:
        hourly = get_hourly_breakdown(today, db_path=settings.resolved_db_path())
        hourly_df = pd.DataFrame([
            {
                "hour": f"{bucket.hour:02d}:00",
                "productive": bucket.productive_seconds,
                "distracting": bucket.distracting_seconds,
                "background": bucket.background_seconds,
                "system": bucket.system_seconds,
                "unknown": bucket.unknown_seconds,
            }
            for bucket in hourly
        ])
        chart_df = hourly_df.melt(id_vars=["hour"], var_name="category", value_name="seconds")
        fig = px.bar(
            chart_df,
            x="hour",
            y="seconds",
            color="category",
            barmode="stack",
            color_discrete_map=CATEGORY_COLORS,
            title="Hourly Activity",
        )
        st.plotly_chart(fig, use_container_width=True)

    domains = get_top_domains(limit=10, db_path=settings.resolved_db_path())
    domain_df = pd.DataFrame([asdict(item) for item in domains])
    st.subheader("Top Domains")
    st.dataframe(domain_df, use_container_width=True, hide_index=True)



def _render_history(settings: Settings) -> None:
    st.header("History")
    weeks = st.slider("Weeks", min_value=1, max_value=12, value=4)
    trend = get_weekly_trend(weeks=weeks, db_path=settings.resolved_db_path())
    trend_df = pd.DataFrame(
        [
            {
                "day": item.day.isoformat(),
                "score": item.score,
                "productive": item.productive_seconds,
                "distracting": item.distracting_seconds,
                "background": item.background_seconds,
                "system": item.system_seconds,
                "unknown": item.unknown_seconds,
            }
            for item in trend
        ]
    )

    fig = px.line(trend_df, x="day", y="score", title="Weekly Productivity Trend")
    fig.update_traces(line_color=CHART_PALETTE[0])
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Per-day Breakdown")
    st.dataframe(trend_df, use_container_width=True, hide_index=True)



def _render_rules(settings: Settings) -> None:
    st.header("Rules")
    rules_path = settings.resolved_rules_path()
    if not rules_path.exists():
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(
            yaml.safe_dump(
                {
                    "productive": [],
                    "distracting": [],
                    "background": [],
                    "system": [],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    current = rules_path.read_text(encoding="utf-8")
    edited = st.text_area("Edit rules.yaml", value=current, height=420)
    if st.button("Save rules"):
        try:
            parsed = yaml.safe_load(edited) or {}
            if not isinstance(parsed, dict):
                raise ValueError("Rules must be a mapping")
            rules_path.write_text(yaml.safe_dump(parsed, sort_keys=False), encoding="utf-8")
            st.success("Rules saved")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to save rules: {exc}")



def _render_settings(settings: Settings) -> None:
    st.header("Settings")

    poll_interval = st.number_input(
        "Poll interval (seconds)",
        min_value=1,
        max_value=60,
        value=settings.poll_interval_seconds,
    )
    ollama_endpoint = st.text_input("Ollama endpoint", value=settings.ollama_endpoint)
    ollama_model = st.text_input("Ollama model", value=settings.ollama_model)
    dark_mode = st.toggle("Dark mode", value=settings.theme.lower() == "dark")

    if st.button("Save settings"):
        settings_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        payload = {
            "poll_interval_seconds": int(poll_interval),
            "ollama_endpoint": ollama_endpoint,
            "ollama_model": ollama_model,
            "db_path": settings.db_path,
            "rules_path": settings.rules_path,
            "log_level": settings.log_level,
            "theme": "dark" if dark_mode else "light",
        }
        settings_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        st.success("Settings saved")


if __name__ == "__main__":
    run_app()
