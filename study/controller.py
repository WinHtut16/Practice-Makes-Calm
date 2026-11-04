"""Adaptive resistance controller (deterministic code, not an LLM).

L_{t+1} = max(L-1, 1)  if stress >= 8 or DESC <= 2     ("lower" is checked first)
          min(L+1, 3)  if stress <= 6 and DESC >= 5   (raise threshold lowered from 6 after pilot P4)
          L            otherwise
"""
from django.conf import settings


def next_level(level, stress, desc, cfg=None):
    c = cfg or settings.STUDY
    if stress >= c["LOWER_IF_STRESS_GE"] or desc <= c["LOWER_IF_DESC_LE"]:
        return max(level - 1, 1), "lower"
    if stress <= c["RAISE_IF_STRESS_LE"] and desc >= c["RAISE_IF_DESC_GE"]:
        return min(level + 1, 3), "raise"
    return level, "keep"
