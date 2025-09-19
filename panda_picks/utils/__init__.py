"""Utility functions for the Panda Picks package."""

# Re-export normalizer helpers for convenience
try:
    from .team_normalizer import normalize_team, normalize_df_team_cols  # noqa: F401
except Exception:
    # Optional at import time if CSV missing; tests can still import directly
    pass
