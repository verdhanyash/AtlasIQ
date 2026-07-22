
"""AtlasIQ Streamlit Frontend Application.

A modern enterprise RAG platform UI with Liquid Glass aesthetics. This is NOT a
chatbot interface - it's a knowledge search platform where users ask questions
and receive evidence-backed answers with citations.

Design Philosophy:
- Liquid Glass / Glassmorphism aesthetic (dark theme)
- Premium, minimal, trustworthy
- Evidence-backed answers with inline citations
- Confidence indicators and guardrails
- Inspired by: Perplexity AI, NotebookLM, Apple, Notion, Linear
"""

from __future__ import annotations

import base64
import html
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

# Configure page — must be the first Streamlit command
st.set_page_config(
    page_title="AtlasIQ | Enterprise Knowledge Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = os.getenv("ATLASIQ_API_URL", "http://localhost:8000")
QUERY_ENDPOINT = f"{API_BASE_URL}/query"
DOCUMENTS_ENDPOINT = f"{API_BASE_URL}/ingest/documents"
UPLOAD_ENDPOINT = f"{API_BASE_URL}/ingest/upload"

# Rate limiting configuration
MAX_REQUESTS_PER_MINUTE = 20

# ─── Session State Defaults ──────────────────────────────────────────────────

if "query_result" not in st.session_state:
    st.session_state.query_result = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "request_timestamps" not in st.session_state:
    st.session_state.request_timestamps = []
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = "Mock (Local Demo)"
if "llm_model" not in st.session_state:
    st.session_state.llm_model = None
if "llm_api_key" not in st.session_state:
    st.session_state.llm_api_key = None

# ─── Custom CSS: Liquid Glass Design System ──────────────────────────────────

CUSTOM_CSS = """
<style>
/* ═══ Font Imports ═══ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

/* ═══ CSS Custom Properties ═══ */
:root {
    --surface: #0e0e0e;
    --surface-dim: #141313;
    --surface-bright: #3a3939;
    --surface-container-lowest: #0e0e0e;
    --surface-container-low: #1c1b1b;
    --surface-container: #201f1f;
    --surface-container-high: #2a2a2a;
    --surface-container-highest: #353434;
    --on-surface: #e5e2e1;
    --on-surface-variant: #c4c7c8;
    --outline: #8e9192;
    --outline-variant: #444748;
    --primary: #ffffff;
    --on-primary: #2f3131;
    --secondary: #c6c6cf;
    --error: #ffb4ab;
    --success: #4CAF50;
    --success-muted: rgba(76, 175, 80, 0.12);
    --warning: #F59E0B;
    --warning-muted: rgba(245, 158, 11, 0.12);
    --error-muted: rgba(255, 180, 171, 0.12);
}

/* ═══ Material Symbols ═══ */
.material-symbols-outlined {
    font-family: 'Material Symbols Outlined';
    font-weight: normal;
    font-style: normal;
    font-size: 20px;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -webkit-font-smoothing: antialiased;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

/* ═══ Hide Streamlit Chrome ═══ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stDecoration"] {display: none;}
div[data-testid="stToolbar"] {display: none;}

/* Use Streamlit sidebar in fixed position - styled as Stitch design */
section[data-testid="stSidebar"] {
    background: rgba(32, 31, 31, 0.3) !important;
    backdrop-filter: blur(40px) !important;
    -webkit-backdrop-filter: blur(40px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.10) !important;
    width: 240px !important;
}

section[data-testid="stSidebar"] > div {
    background: transparent !important;
    padding-top: 40px !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarCollapse Button"] {
    display: none !important;
}

/* ═══ Body & App ═══ */
.stApp {
    background-color: var(--surface) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--on-surface);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ═══ Ambient Background Orbs ═══ */
.stApp::before {
    content: '';
    position: fixed;
    top: -20%;
    left: -10%;
    width: 600px;
    height: 600px;
    background: rgba(255, 255, 255, 0.025);
    filter: blur(120px);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
}
.stApp::after {
    content: '';
    position: fixed;
    bottom: 10%;
    right: -5%;
    width: 400px;
    height: 400px;
    background: rgba(255, 255, 255, 0.015);
    filter: blur(100px);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
}

/* ═══ Sidebar: Liquid Glass Level 1 ═══ */
section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    width: 260px !important;
}

section[data-testid="stSidebar"] > div {
    background: transparent !important;
    padding-top: 2rem !important;
}

section[data-testid="stSidebar"] .stMarkdown {
    color: var(--on-surface);
}

/* ═══ Liquid Glass Layers ═══ */
.liquid-glass-1 {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.liquid-glass-2 {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(32px);
    -webkit-backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.10);
}

.liquid-glass-3 {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(40px);
    -webkit-backdrop-filter: blur(40px);
    border: 1px solid rgba(255, 255, 255, 0.12);
}

/* ═══ Text Input: Glass Pill ═══ */
.stTextInput > div > div > input {
    background: rgba(255, 255, 255, 0.04) !important;
    backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    border-radius: 99px !important;
    color: var(--on-surface) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 16px !important;
    padding: 14px 24px 14px 48px !important;
    height: 56px !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    caret-color: var(--primary);
}

.stTextInput > div > div > input::placeholder {
    color: var(--on-surface-variant) !important;
    opacity: 0.5;
}

.stTextInput > div > div > input:focus {
    border-color: rgba(255, 255, 255, 0.35) !important;
    box-shadow: 0 0 20px 0 rgba(255, 255, 255, 0.10) !important;
    outline: none !important;
}

.stTextInput label {
    display: none !important;
}

/* ═══ Buttons: Glass ═══ */
.stButton > button {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    border-radius: 10px !important;
    color: var(--on-surface) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
    padding: 12px 24px !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    min-height: 44px;
}

.stButton > button:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.18) !important;
    box-shadow: 0 0 20px 0 rgba(255, 255, 255, 0.08) !important;
    transform: translateY(-1px);
}

.stButton > button:active {
    transform: translateY(0) scale(0.98);
}

/* Primary Button */
.stButton > button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"] {
    background: var(--primary) !important;
    color: var(--on-primary) !important;
    border: none !important;
    font-weight: 600 !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 24px 0 rgba(255, 255, 255, 0.15) !important;
}

/* ═══ Typography ═══ */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
    color: var(--on-surface) !important;
    font-weight: 600;
}

/* ═══ File Uploader ═══ */
section[data-testid="stFileUploader"] {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px;
}

section[data-testid="stFileUploader"] label {
    color: var(--on-surface-variant) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}

/* ═══ Expander ═══ */
details[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
}

details[data-testid="stExpander"] summary {
    color: var(--on-surface) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* ═══ Status Messages ═══ */
div[data-testid="stAlert"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    border-left: 3px solid var(--outline) !important;
    color: var(--on-surface) !important;
}

/* ═══ Spinner ═══ */
div[data-testid="stSpinner"] > div {
    border-top-color: var(--primary) !important;
}

/* ═══ Animations ═══ */
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 8px 0 rgba(76, 175, 80, 0.15); }
    50% { box-shadow: 0 0 16px 0 rgba(76, 175, 80, 0.25); }
}

.loading-shimmer {
    background: linear-gradient(90deg,
        rgba(255,255,255,0.03) 25%,
        rgba(255,255,255,0.07) 50%,
        rgba(255,255,255,0.03) 75%);
    background-size: 200% 100%;
    animation: shimmer 2s infinite linear;
}

.fade-in {
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    opacity: 0;
}

.fade-in-d1 { animation-delay: 0.1s; }
.fade-in-d2 { animation-delay: 0.2s; }
.fade-in-d3 { animation-delay: 0.3s; }
.fade-in-d4 { animation-delay: 0.4s; }
.fade-in-d5 { animation-delay: 0.5s; }
.fade-in-d6 { animation-delay: 0.6s; }
.fade-in-d7 { animation-delay: 0.7s; }

/* ═══ Custom Component Classes ═══ */

/* Glass Card */
.glass-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(32px);
    -webkit-backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 16px;
    padding: 28px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.glass-card:hover {
    border-color: rgba(255, 255, 255, 0.18);
}

/* Elevated Glass Card */
.glass-card-elevated {
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(40px);
    -webkit-backdrop-filter: blur(40px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 20px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.glass-card-elevated:hover {
    border-color: rgba(255, 255, 255, 0.20);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

/* Accent Bar (left side of answer card) */
.accent-bar-success {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: rgba(76, 175, 80, 0.5);
    border-radius: 0 2px 2px 0;
}

.accent-bar-warning {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: rgba(245, 158, 11, 0.5);
    border-radius: 0 2px 2px 0;
}

.accent-bar-error {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: rgba(255, 180, 171, 0.5);
    border-radius: 0 2px 2px 0;
}

/* Confidence Badge */
.confidence-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 14px;
    border-radius: 99px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.confidence-high {
    background: rgba(76, 175, 80, 0.10);
    border: 1px solid rgba(76, 175, 80, 0.20);
    color: #4CAF50;
}

.confidence-medium {
    background: rgba(245, 158, 11, 0.10);
    border: 1px solid rgba(245, 158, 11, 0.20);
    color: #F59E0B;
}

.confidence-low {
    background: rgba(255, 180, 171, 0.10);
    border: 1px solid rgba(255, 180, 171, 0.20);
    color: #ffb4ab;
}

/* Citation Badge (inline superscript) */
.citation-sup {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    padding: 1px 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    color: var(--primary);
    vertical-align: super;
    line-height: 1;
    margin: 0 2px;
    cursor: default;
}

/* Citation Underline */
.citation-underline {
    text-decoration: underline;
    text-underline-offset: 4px;
    text-decoration-thickness: 1px;
    text-decoration-color: rgba(255, 255, 255, 0.25);
}

/* Source Index Badge */
.source-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    background: rgba(255, 255, 255, 0.10);
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    color: var(--on-surface);
}

/* Quote Block */
.quote-block {
    background: rgba(14, 14, 14, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
}

/* Label Typography */
.label-sm {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--on-surface-variant);
    opacity: 0.6;
}

.label-md {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: var(--on-surface);
}

/* Example Card */
.example-card {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 22px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.example-card:hover {
    background: rgba(255, 255, 255, 0.07);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 0 20px 0 rgba(255, 255, 255, 0.06);
    transform: translateY(-2px);
}

.example-category {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--on-surface-variant);
    opacity: 0.5;
    margin-bottom: 8px;
}

/* Nav Item */
.nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: var(--on-surface-variant);
    transition: all 0.2s ease;
    cursor: pointer;
}

.nav-item:hover {
    background: rgba(255, 255, 255, 0.06);
}

.nav-item-active {
    background: rgba(255, 255, 255, 0.07);
    color: var(--primary);
    font-weight: 600;
}

/* Status Bar */
.status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 24px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--on-surface-variant);
    opacity: 0.5;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4CAF50;
    margin-right: 8px;
    animation: pulseGlow 2s infinite;
}

/* Source Avatars */
.source-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.10);
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    color: var(--on-surface);
    margin-left: -6px;
}

.source-avatar:first-child {
    margin-left: 0;
}

/* Action Button */
.action-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 22px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.10);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: var(--on-surface-variant);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.action-btn:hover {
    color: var(--primary);
    border-color: rgba(255, 255, 255, 0.18);
}

.action-btn-primary {
    background: var(--primary);
    color: var(--on-primary);
    border: none;
}

.action-btn-primary:hover {
    box-shadow: 0 0 24px 0 rgba(255, 255, 255, 0.15);
}

/* Top Bar */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

/* Sidebar Divider */
.sidebar-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.06);
    margin: 16px 0;
}

/* Upload Button (sidebar) */
.upload-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 12px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.10);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: var(--primary);
    cursor: pointer;
    transition: all 0.3s ease;
}

.upload-btn:hover {
    box-shadow: 0 0 20px 0 rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.08);
}

/* Streamlit columns gap fix */
div[data-testid="stHorizontalBlock"] {
    gap: 16px;
}

/* Hide default label for inputs */
.stTextInput label,
.stFileUploader label p {
    display: none !important;
}

/* Sidebar toggle button in top bar — compact glass icon */
button[aria-label*="sidebar"] {
    width: 34px !important;
    height: 34px !important;
    min-height: 34px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 18px !important;
    line-height: 1 !important;
    border-radius: 8px !important;
    background: rgba(255, 255, 255, 0.04) !important;
    backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: var(--on-surface-variant) !important;
    transition: all 0.2s ease !important;
    flex-shrink: 0 !important;
}

button[aria-label*="sidebar"]:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.16) !important;
    color: var(--primary) !important;
}

button[aria-label*="sidebar"]:active {
    transform: scale(0.92) !important;
}

/* Hamburger button styling */
button[key="hamburger_btn"] {
    width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    display: none !important; /* Hide the Streamlit button, use custom HTML */
}

/* Scrollbar - hidden but functional */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.15); }

</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─── Helper Functions ─────────────────────────────────────────────────────────


def _icon(name: str, fill: bool = False, size: str = "20px", color: str = "") -> str:
    """Render a Material Symbols Outlined icon as inline HTML."""
    fill_val = "1" if fill else "0"
    style_parts = [
        f"font-size: {size}",
        f"font-variation-settings: 'FILL' {fill_val}, 'wght' 400, 'GRAD' 0, 'opsz' 24",
    ]
    if color:
        style_parts.append(f"color: {color}")
    style = "; ".join(style_parts)
    return f'<span class="material-symbols-outlined" style="{style}">{name}</span>'


def _get_logo_base64() -> str:
    """Load and encode the logo image as base64 for embedding."""
    logo_path = Path(__file__).parent / "static" / "logo.png"
    try:
        with open(logo_path, "rb") as f:
            logo_bytes = f.read()
            return base64.b64encode(logo_bytes).decode()
    except Exception as e:
        logger.warning(f"Could not load logo: {e}")
        return ""


def format_confidence_badge(confidence: float) -> str:
    """Return HTML for a confidence badge pill."""
    if confidence >= 0.7:
        css_class = "confidence-high"
        label = "High Confidence"
        icon_color = "#4CAF50"
    elif confidence >= 0.4:
        css_class = "confidence-medium"
        label = "Medium Confidence"
        icon_color = "#F59E0B"
    else:
        css_class = "confidence-low"
        label = "Low Confidence"
        icon_color = "#ffb4ab"

    pct = f"{confidence * 100:.0f}%"
    check = _icon("check_circle", fill=True, size="14px", color=icon_color)
    return (
        f'<div class="confidence-badge {css_class}">'
        f'{check} {label} ({pct})'
        f'</div>'
    )


def render_citation_badge(index: int) -> str:
    """Render an inline citation superscript badge."""
    return f'<span class="citation-sup">{index}</span>'


def render_answer_with_citations(answer: str, citations: list[dict[str, Any]]) -> str:
    """Replace [N] citation markers with styled inline badges.
    
    Validates that citation indices are within bounds of actual citations list.
    """
    pattern = r"\[(\d+)\]"

    def replace_citation(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        # Validate citation index
        if idx < 1 or idx > len(citations):
            logger.warning(f"Citation index {idx} out of bounds (have {len(citations)} citations)")
            return f'<span class="citation-sup" style="background: rgba(255,0,0,0.2);">{idx}</span>'
        return render_citation_badge(idx)

    return re.sub(pattern, replace_citation, answer)


# ─── Cached API Calls ─────────────────────────────────────────────────────────


@st.cache_data(ttl=300, max_entries=10, show_spinner=False)
def _fetch_documents() -> list[dict[str, Any]]:
    """Fetch the document list from the API with caching to reduce latency.
    
    Cache expires after 5 minutes and stores max 10 entries to prevent memory leaks.
    """
    try:
        response = httpx.get(DOCUMENTS_ENDPOINT, params={"limit": 50}, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        docs: list[dict[str, Any]] = data.get("documents", [])
        return docs
    except httpx.HTTPError:
        raise  # Let the caller handle unavailable backend


def render_sidebar() -> None:
    """Render the fixed left sidebar matching Stitch design.
    
    Uses Streamlit's native sidebar - no reruns, instant response.
    """
    with st.sidebar:
        # ── Branding ──
        logo_base64 = _get_logo_base64()
        if logo_base64:
            logo_img = f'<img src="data:image/png;base64,{logo_base64}" style="width: 32px; height: 32px; border-radius: 8px;" alt="AtlasIQ Logo">'
        else:
            logo_img = f'<div style="width: 32px; height: 32px; border-radius: 8px; background: var(--primary); display: flex; align-items: center; justify-content: center;">{_icon("dataset", fill=True, size="20px", color="var(--on-primary)")}</div>'
        
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 32px;">
                {logo_img}
                <div>
                    <h1 style="font-size: 24px; margin: 0; line-height: 1.3; font-weight: 700;">
                        AtlasIQ
                    </h1>
                    <p style="font-family: 'JetBrains Mono', monospace; font-size: 12px;
                       color: var(--on-surface-variant); opacity: 0.6; margin: 0;">
                        Enterprise RAG
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # ── Navigation ──
        st.markdown('<div style="margin-bottom: 24px;"></div>', unsafe_allow_html=True)
        
        # Document Library (Active)
        if st.button("📁 Document Library", key="nav_library", use_container_width=True):
            pass  # Already on this page
        
        #Collections
        if st.button("📚 Collections", key="nav_collections", use_container_width=True):
            st.info("Collections feature coming soon!")
        
        # Settings (Expander)
        with st.expander("⚙️ Settings", expanded=False):
            provider_choice = st.selectbox(
                "LLM Provider",
                options=["Mock (Local Demo)", "Ollama (Local Server)", "NVIDIA Build API", "OpenAI API"],
                index=0,
                key="llm_provider_select",
            )
            
            st.session_state.llm_provider = provider_choice

            if "Mock" in provider_choice:
                st.caption("⚡ Uses built-in synthesis")
                st.session_state.llm_model = None
                st.session_state.llm_api_key = None
            elif "Ollama" in provider_choice:
                ollama_model = st.text_input("Model", value="gemma3:4b", key="ollama_model")
                ollama_url = st.text_input("URL", value="http://localhost:11434", key="ollama_url")
                st.session_state.llm_model = ollama_model
                st.session_state.llm_api_url = ollama_url
            elif "NVIDIA" in provider_choice:
                nvidia_model = st.text_input("Model", value="meta/llama-3.1-405b-instruct", key="nvidia_model")
                nvidia_key = st.text_input("API Key", type="password", key="nvidia_key")
                st.session_state.llm_model = nvidia_model
                st.session_state.llm_api_key = nvidia_key
            elif "OpenAI" in provider_choice:
                openai_model = st.text_input("Model", value="gpt-4o-mini", key="openai_model")
                openai_key = st.text_input("API Key", type="password", key="openai_key")
                st.session_state.llm_model = openai_model
                st.session_state.llm_api_key = openai_key
        
        st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
        
        # User Profile
        if st.button("👤 User Profile", key="nav_profile", use_container_width=True):
            st.info("User profile feature coming soon!")
        
        st.markdown('<div style="margin-top: auto;"></div>', unsafe_allow_html=True)
        
        # ── Upload Button ──
        st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Upload Documents",
            type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=True,
            key="sidebar_uploader",
        )

        if uploaded_files:
            with st.spinner("Indexing..."):
                for uploaded_file in uploaded_files:
                    try:
                        file_content = uploaded_file.getvalue()
                        files = {"file": (uploaded_file.name, file_content, uploaded_file.type)}
                        response = httpx.post(UPLOAD_ENDPOINT, files=files, timeout=60.0)
                        response.raise_for_status()
                        result = response.json()

                        if result["status"] in ("new", "modified"):
                            st.success(f"✓ {uploaded_file.name}")
                            _fetch_documents.clear()
                        else:
                            st.info(f"◌ {uploaded_file.name} unchanged")
                    except httpx.HTTPStatusError as e:
                        st.error(f"✗ {uploaded_file.name}: HTTP {e.response.status_code}")
                    except httpx.RequestError:
                        st.error(f"✗ {uploaded_file.name}: Network error")
                    except Exception as e:
                        st.error(f"✗ {uploaded_file.name}: Error")
                        logger.exception("Upload error: %s", e)


# ─── Top Bar ─────────────────────────────────────────────────────────────────


def render_top_bar() -> None:
    """Render the top app bar matching Stitch design."""
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between;
                    padding: 16px 40px; border-bottom: 1px solid rgba(255,255,255,0.05);">
            <div>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px;
                             color: var(--on-surface-variant); letter-spacing: 0.08em;
                             text-transform: uppercase;">
                    KNOWLEDGE SEARCH
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="cursor: pointer; opacity: 0.6; transition: opacity 0.2s;"
                     onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.6'">
                    {_icon("notifications", size="20px")}
                </div>
                <div style="cursor: pointer; opacity: 0.6; transition: opacity 0.2s;"
                     onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.6'">
                    {_icon("help_outline", size="20px")}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Home View (content only, no search bar) ────────────────────────────────


def render_home_hero() -> None:
    """Render the home hero section above the search bar."""
    st.markdown(
        f"""
        <div style="text-align: center; margin: 60px 0 12px 0;" class="fade-in">
            <div style="display: inline-flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                {_icon("search", size="36px", color="var(--on-surface-variant)")}
                <div style="width: 40px; height: 40px; border-radius: 10px;
                            background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
                            display: inline-flex; align-items: center; justify-content: center;">
                    {_icon("eco", fill=True, size="22px", color="var(--primary)")}
                </div>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 28px;
                             font-weight: 700; letter-spacing: -0.02em;">RK</span>
            </div>
            <h1 style="font-size: 36px; font-weight: 600; letter-spacing: -0.02em;
                       margin: 0; line-height: 1.2;">
                How can I help you today?
            </h1>
            <p style="font-size: 16px; color: var(--on-surface-variant); margin-top: 10px;
                      opacity: 0.7; line-height: 1.5;">
                Get started by asking a question about your documents.<br>
                AtlasIQ parses your enterprise data in seconds.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_example_cards() -> None:
    """Render example query cards below the search bar on the home view."""
    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)

    examples = [
        {"category": "FINANCE", "icon": "trending_up",
         "question": "What is the projected revenue for Q4?"},
        {"category": "ANALYSIS", "icon": "description",
         "question": "Summarize the market analysis report."},
        {"category": "LEGAL", "icon": "gavel",
         "question": "Review the termination clauses in current vendor contracts."},
        {"category": "STRATEGY", "icon": "hub",
         "question": "Identify cross-departmental synergy opportunities."},
    ]

    col1, col2 = st.columns(2)

    for idx, ex in enumerate(examples):
        with [col1, col2][idx % 2]:
            st.markdown(
                f"""
                <div class="example-card fade-in fade-in-d{idx + 2}">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        {_icon(ex["icon"], size="18px", color="var(--on-surface-variant)")}
                        <span class="example-category">{ex["category"]}</span>
                    </div>
                    <p style="font-size: 15px; margin: 0; line-height: 1.5;
                              color: var(--on-surface);">
                        {ex["question"]}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"💬 {ex['question'][:40]}",
                key=f"example_{idx}",
                use_container_width=True,
            ):
                st.session_state["submitted_query"] = ex["question"]
                st.rerun()

    # Footer Stats
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 48px; padding: 16px 0;">
            <p style="font-family: 'JetBrains Mono', monospace; font-size: 11px;
                      color: var(--on-surface-variant); opacity: 0.35;">
                {_icon("info", size="14px", color="var(--on-surface-variant)")}
                AtlasIQ searches across your indexed enterprise documents
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Query Execution ─────────────────────────────────────────────────────────


def _check_rate_limit() -> bool:
    """Check if user is within rate limit.
    
    Returns True if request is allowed, False if rate limit exceeded.
    """
    current_time = time.time()
    # Remove timestamps older than 60 seconds
    st.session_state.request_timestamps = [
        ts for ts in st.session_state.request_timestamps 
        if current_time - ts < 60
    ]
    
    if len(st.session_state.request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    st.session_state.request_timestamps.append(current_time)
    return True


def _execute_query(question: str) -> None:
    """Execute a query against the backend and render results inline.
    
    Includes input validation, rate limiting, timeout handling, and proper error messages.
    """
    # Input validation
    if not question or not question.strip():
        st.error("Please enter a valid question.")
        return
    
    question = question.strip()
    if len(question) > 1000:
        st.error("Question is too long. Please limit to 1000 characters.")
        return
    
    # Rate limiting
    if not _check_rate_limit():
        st.warning(f"⏱️ Rate limit exceeded. Please wait before making another request. (Max {MAX_REQUESTS_PER_MINUTE}/min)")
        return
    
    st.session_state.last_query = question

    try:
        with st.spinner("Retrieving evidence..."):
            # Build request payload with LLM settings
            payload = {"question": question}
            
            # Add LLM provider settings if configured
            if st.session_state.get("llm_provider") and st.session_state.llm_provider != "Mock (Local Demo)":
                payload["provider"] = st.session_state.llm_provider
                if st.session_state.get("llm_model"):
                    payload["model"] = st.session_state.llm_model
                if st.session_state.get("llm_api_key"):
                    payload["api_key"] = st.session_state.llm_api_key
                if st.session_state.get("llm_api_url"):
                    payload["api_url"] = st.session_state.llm_api_url
            
            response = httpx.post(
                QUERY_ENDPOINT,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        st.session_state.query_result = result
        render_results_view(result, question)

    except httpx.TimeoutException:
        st.markdown(
            f"""
            <div class="glass-card fade-in" style="margin-top: 24px;">
                <div class="accent-bar-warning"></div>
                <div style="padding-left: 16px;">
                    <p style="font-size: 15px; color: var(--warning); margin: 0 0 8px 0;">
                        {_icon("schedule", size="18px", color="var(--warning)")}
                        Request timed out
                    </p>
                    <p style="font-family: 'JetBrains Mono', monospace; font-size: 12px;
                              color: var(--on-surface-variant); margin: 0;">
                        The query took too long to process. Please try again or rephrase your question.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except httpx.HTTPStatusError as e:
        # Escape error message to prevent XSS
        safe_error = html.escape(str(e.response.text[:200]))
        st.markdown(
            f"""
            <div class="glass-card fade-in" style="margin-top: 24px;">
                <div class="accent-bar-error"></div>
                <div style="padding-left: 16px;">
                    <p style="font-size: 15px; color: var(--error); margin: 0 0 8px 0;">
                        {_icon("error", size="18px", color="var(--error)")}
                        Query failed
                    </p>
                    <p style="font-family: 'JetBrains Mono', monospace; font-size: 12px;
                              color: var(--on-surface-variant); margin: 0;">
                        {e.response.status_code} — {safe_error}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        logger.error(f"Query HTTP error: {e}")
    except httpx.RequestError as e:
        st.markdown(
            f"""
            <div class="glass-card fade-in" style="margin-top: 24px;">
                <div class="accent-bar-warning"></div>
                <div style="padding-left: 16px;">
                    <p style="font-size: 15px; color: var(--warning); margin: 0 0 8px 0;">
                        {_icon("cloud_off", size="18px", color="var(--warning)")}
                        Backend unavailable
                    </p>
                    <p style="font-family: 'JetBrains Mono', monospace; font-size: 12px;
                              color: var(--on-surface-variant); margin: 0;">
                        Could not connect to the AtlasIQ backend. Start the backend first:
                    </p>
                    <code style="display: block; margin-top: 8px; padding: 10px 14px;
                                 background: rgba(255,255,255,0.04); border-radius: 8px;
                                 border: 1px solid rgba(255,255,255,0.06);
                                 font-family: 'JetBrains Mono', monospace; font-size: 12px;
                                 color: var(--on-surface);">
                        .venv\\Scripts\\python.exe -m atlasiq.backend.main
                    </code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        logger.error(f"Query network error: {e}")
    except Exception as e:
        st.error("An unexpected error occurred during query processing.")
        logger.exception("Query processing error: %s", e)


# ─── Results View ─────────────────────────────────────────────────────────────


def render_results_view(result: dict[str, Any], question: str) -> None:
    """Render the full answer results view with citations."""
    # ── Confidence Badge ──
    confidence_html = format_confidence_badge(result["confidence"])

    # Determine accent bar
    if result["confidence"] >= 0.7:
        accent_class = "accent-bar-success"
    elif result["confidence"] >= 0.4:
        accent_class = "accent-bar-warning"
    else:
        accent_class = "accent-bar-error"

    # ── Answer Card ──
    st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

    if result.get("refusal_reason"):
        # Guardrail refusal
        st.markdown(
            f"""
            <div class="glass-card fade-in fade-in-d1" style="padding-left: 32px;">
                <div class="accent-bar-warning"></div>
                <div style="margin-bottom: 16px;">
                    <div class="confidence-badge confidence-medium">
                        {_icon("shield", fill=True, size="14px", color="#F59E0B")}
                        Guardrail Active
                    </div>
                </div>
                <p style="font-size: 16px; line-height: 1.7; margin: 0 0 12px 0;
                          color: var(--on-surface);">
                    {result['answer']}
                </p>
                <p style="font-family: 'JetBrains Mono', monospace; font-size: 12px;
                          color: var(--on-surface-variant); opacity: 0.6; margin: 0;">
                    Reason: {result['refusal_reason']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Normal answer
        import textwrap

        formatted_answer = render_answer_with_citations(result["answer"], result["citations"])
        num_sources = len(result.get("sources", []))

        # Source avatars
        avatars_html = ""
        for _, src in enumerate(result.get("sources", [])[:3]):
            letter = src[0].upper() if src else "?"
            avatars_html += f'<span class="source-avatar">{letter}</span>'

        card_html = textwrap.dedent(
            f"""
            <div class="glass-card fade-in fade-in-d1" style="padding-left: 32px;">
                <div class="{accent_class}"></div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                    {confidence_html}
                    <div style="display: flex; align-items: center; gap: 16px; color: rgba(255,255,255,0.25);">
                        {_icon("content_copy", size="16px")}
                        {_icon("thumb_up", size="16px")}
                        {_icon("thumb_down", size="16px")}
                    </div>
                </div>
                <div style="font-size: 16px; line-height: 1.7; color: var(--on-surface);">
                    {formatted_answer}
                </div>
                <div style="display: flex; align-items: center; gap: 12px; padding-top: 20px; margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.08);">
                    <span class="label-sm" style="opacity: 0.35;">Synthesized from {num_sources} source{"s" if num_sources != 1 else ""}</span>
                    <div style="display: flex; align-items: center;">{avatars_html}</div>
                </div>
            </div>
            """
        )
        st.markdown(card_html, unsafe_allow_html=True)

    # ── Citation Grid ──
    citations = result.get("citations", [])
    if citations:
        st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between;
                        padding: 0 4px; margin-bottom: 16px;" class="fade-in fade-in-d3">
                <span class="label-sm" style="opacity: 0.5;">VERIFIED SOURCES</span>
                <span class="label-sm" style="opacity: 0.4; cursor: pointer;">
                    View All {_icon("arrow_forward", size="12px")}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        num_cols = min(3, len(citations))
        cols = st.columns(num_cols)

        for idx, citation in enumerate(citations):
            col_idx = idx % num_cols
            with cols[col_idx]:
                # FIX: Escape all user-provided data to prevent XSS
                doc_name = html.escape(citation["document_name"])
                display_name = doc_name if len(doc_name) <= 28 else doc_name[:25] + "..."
                quote = html.escape(citation["quote"])
                display_quote = quote if len(quote) <= 120 else quote[:117] + "..."
                page_label = html.escape(str(citation["page"]))
                ext = doc_name.rsplit(".", 1)[-1].upper() if "." in doc_name else "DOC"
                delay_class = f"fade-in-d{min(idx + 3, 7)}"

                st.markdown(
                    f"""
                    <div class="glass-card-elevated fade-in {delay_class}"
                         style="display: flex; flex-direction: column; gap: 14px;
                                min-height: 200px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="source-index">{idx + 1}</span>
                            <span style="font-family: 'JetBrains Mono', monospace;
                                         font-size: 12px; font-weight: 500;
                                         white-space: nowrap; overflow: hidden;
                                         text-overflow: ellipsis;">
                                {display_name}
                            </span>
                        </div>
                        <div class="quote-block">
                            <p style="font-family: 'JetBrains Mono', monospace;
                                      font-size: 10px; font-weight: 600;
                                      color: var(--on-surface-variant); opacity: 0.6;
                                      margin: 0 0 6px 0; letter-spacing: 0.04em;
                                      text-transform: uppercase;">
                                PAGE {page_label}
                            </p>
                            <p style="font-family: 'JetBrains Mono', monospace;
                                      font-size: 12px; line-height: 1.6;
                                      color: rgba(229, 226, 225, 0.7);
                                      font-style: italic; margin: 0;">
                                "{display_quote}"
                            </p>
                        </div>
                        <div style="display: flex; align-items: center;
                                    justify-content: space-between; margin-top: auto;">
                            <span style="font-family: 'JetBrains Mono', monospace;
                                         font-size: 10px; color: var(--on-surface-variant);
                                         opacity: 0.4; text-transform: uppercase;">
                                {ext}
                            </span>
                            {_icon("open_in_new", size="14px", color="var(--on-surface-variant)")}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Action Footer ──
    st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

    act_col1, act_col2, act_col3 = st.columns(3)
    with act_col1:
        if st.button("↻ Regenerate", key="btn_regen", use_container_width=True):
            st.session_state["submitted_query"] = question
            st.rerun()
    with act_col2:
        st.button("↗ Share Result", key="btn_share", use_container_width=True)
    with act_col3:
        st.button("📊 Deep Analysis", key="btn_deep", type="primary", use_container_width=True)


# ─── Status Bar ──────────────────────────────────────────────────────────────


def render_status_bar() -> None:
    """Render the bottom status bar."""
    st.markdown(
        """
        <div class="status-bar" style="margin-top: 32px;">
            <div style="display: flex; align-items: center;">
                <span class="status-dot"></span>
                <span>System Ready</span>
                <span style="margin: 0 8px; opacity: 0.3;">|</span>
                <span>v1.24.0-pro</span>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <span>JetBrains Mono</span>
                <span>Inter</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Main Application ────────────────────────────────────────────────────────


def main() -> None:
    """Main application entry point.

    Architecture:
    1. Render sidebar (always visible, no reruns)
    2. Render top bar
    3. Check for pending query
    4. Render search bar (always visible)
    5. Route to home content OR execute query + show results
    """
    # Render sidebar (always visible)
    render_sidebar()
    
    # Render top bar
    render_top_bar()

    # ── Determine if there is a pending query ──
    pending_query = st.session_state.get("submitted_query", None)
    if pending_query:
        st.session_state["submitted_query"] = None  # Clear after reading

    # ── Decide view mode ──
    has_query = pending_query is not None

    if has_query:
        # ── RESULTS MODE: search bar at top, then results ──
        st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

        col_l, col_c, col_r = st.columns([1, 5, 1])
        with col_c:
            new_question = st.text_input(
                "Search",
                value=pending_query,
                placeholder="Ask anything...",
                label_visibility="collapsed",
                key="query_input",
            )
            btn_l, btn_r = st.columns([3, 1])
            with btn_r:
                search_again = st.button(
                    "Search", type="primary", use_container_width=True, key="search_btn"
                )

        # If user edits the search bar and clicks Search again
        if search_again and new_question and new_question.strip():
            st.session_state["submitted_query"] = new_question.strip()
            st.rerun()

        # Execute the pending query
        _execute_query(pending_query)

    else:
        # ── HOME MODE: hero → search bar → example cards ──
        render_home_hero()

        st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

        col_l, col_c, col_r = st.columns([1, 5, 1])
        with col_c:
            question = st.text_input(
                "Search",
                placeholder="Ask anything...",
                label_visibility="collapsed",
                key="query_input",
            )
            btn_l, btn_r = st.columns([3, 1])
            with btn_r:
                search_clicked = st.button(
                    "Search", type="primary", use_container_width=True, key="search_btn"
                )

        # Handle search button click
        if search_clicked and question and question.strip():
            st.session_state["submitted_query"] = question.strip()
            st.rerun()
        elif search_clicked:
            st.warning("Please enter a question to search.")

        # Show example cards only on home view
        render_example_cards()

    render_status_bar()


if __name__ == "__main__":
    # Backend health check on startup
    try:
        health_response = httpx.get(f"{API_BASE_URL}/health", timeout=2.0)
        if health_response.status_code != 200:
            st.error("⚠️ Backend health check failed. Please ensure the backend is running properly.")
            st.code(f".venv\\Scripts\\python.exe -m atlasiq.backend.main", language="bash")
            logger.warning("Backend health check failed with status %s", health_response.status_code)
    except Exception as e:
        st.warning(
            f"⚠️ Could not connect to backend at {API_BASE_URL}. "
            f"The UI will work but queries will fail until the backend is started."
        )
        st.code(f".venv\\Scripts\\python.exe -m atlasiq.backend.main", language="bash")
        logger.warning("Backend not available: %s", e)
    
    main()

