"""Streamlit embedding of the virtual test bench.

    from virtual_lab.component import render_virtual_lab
    render_virtual_lab()                       # every selectable dataset
    render_virtual_lab(["dynamic_rl"], 1250)   # a subset
"""
from __future__ import annotations

from . import payload as P


def _html(ids: tuple | None) -> str:
    return P.render_html(P.bundle(list(ids) if ids else None))


def render_virtual_lab(dataset_ids=None, height: int = 1250):
    import streamlit as st
    import streamlit.components.v1 as components

    @st.cache_data(show_spinner="Packing simulation records...")
    def cached(ids, stamp):  # stamp invalidates the cache when results/ gains a run
        return _html(ids)

    from .datasets import RESULTS
    stamp = tuple(sorted(p.name for p in RESULTS.iterdir())) if RESULTS.exists() else ()
    ids = tuple(dataset_ids) if dataset_ids else None
    components.html(cached(ids, stamp), height=height, scrolling=True)
