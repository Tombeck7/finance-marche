"""Composants UI Streamlit partagés (layout HTML + widgets natifs pour le contenu)."""

from __future__ import annotations

import html

import streamlit as st

from .theme import (
    ACCENT,
    BG_CARD,
    BG_CARD2,
    BORDER,
    GREEN,
    MUTED,
    RED,
    TEXT,
    YELLOW,
)


def section(title: str) -> None:
    st.markdown(
        f'<div class="section-title">{html.escape(title)}</div>',
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, color: str = TEXT, sub: str = "") -> None:
    sub_html = (
        f'<div style="font-size:11px;color:{MUTED};margin-top:3px;">{html.escape(sub)}</div>'
        if sub
        else ""
    )
    st.markdown(
        f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 18px 12px;">
  <div style="font-size:10px;color:{MUTED};text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px;">{html.escape(label)}</div>
  <div style="font-size:24px;font-weight:700;color:{color};line-height:1.1;">{html.escape(value)}</div>
  {sub_html}
</div>""",
        unsafe_allow_html=True,
    )


def status_pill(label: str, color: str) -> str:
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color};'
        f'border-radius:999px;padding:2px 10px;font-size:10px;font-weight:700;">'
        f"{html.escape(label)}</span>"
    )


def risk_color(score: int) -> str:
    return GREEN if score < 30 else (YELLOW if score < 60 else RED)


def alert_card(
    title: str,
    body: str,
    *,
    priority: str = "",
    border_color: str = YELLOW,
    action: str = "",
) -> None:
    priority_html = (
        f'<div style="color:{border_color};font-size:11px;font-weight:800;">{html.escape(priority)}</div>'
        if priority
        else ""
    )
    action_html = (
        f'<div style="color:{ACCENT};font-size:12px;margin-top:5px;">Action : {html.escape(action)}</div>'
        if action
        else ""
    )
    st.markdown(
        f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {border_color};
            border-radius:9px;padding:12px 14px;margin-bottom:8px;">
  {priority_html}
  <div style="color:{TEXT};font-size:12px;font-weight:700;margin-top:2px;">{html.escape(title)}</div>
  <div style="color:{MUTED};font-size:11px;margin-top:4px;line-height:1.4;">{html.escape(body)}</div>
  {action_html}
</div>""",
        unsafe_allow_html=True,
    )


def demo_banner(step: int, total: int, message: str) -> None:
    if not st.session_state.get("demo_mode"):
        return
    st.markdown(
        f"""
<div style="background:{BG_CARD2};border:1px solid {ACCENT};border-radius:10px;padding:12px 16px;margin-bottom:14px;">
  <div style="color:{ACCENT};font-weight:800;font-size:12px;">Mode démo entretien · Étape {step + 1}/{total}</div>
  <div style="color:{TEXT};font-size:13px;margin-top:4px;line-height:1.45;">{html.escape(message)}</div>
</div>""",
        unsafe_allow_html=True,
    )


def pitch_block(pitch: str) -> None:
    st.info(f"**Pitch 30 sec :** {pitch}")
