"""Statistics feature.

Stats visualization and display.
"""

from .visualizer import generate_stats_image
from .display import send_stats_display, send_text_stats_fallback

__all__ = [
    "generate_stats_image",
    "send_stats_display",
    "send_text_stats_fallback",
]
