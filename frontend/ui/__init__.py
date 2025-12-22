"""
UI shared modules for KE Workbench.

This package contains reusable UI components and helpers used across
the dashboard pages.
"""

from frontend.ui.review_helpers import (
    get_status_color,
    get_status_emoji,
    get_priority_score,
    get_rule_issues,
    submit_review,
)
from frontend.ui.insights import (
    render_tree_view,
    render_chart,
    render_tool_gallery,
    ToolCard,
)
from frontend.ui.worklist import (
    WorklistItem,
    build_worklist,
    render_worklist_item,
    filter_worklist,
)

__all__ = [
    # Review helpers
    "get_status_color",
    "get_status_emoji",
    "get_priority_score",
    "get_rule_issues",
    "submit_review",
    # Insights
    "render_tree_view",
    "render_chart",
    "render_tool_gallery",
    "ToolCard",
    # Worklist
    "WorklistItem",
    "build_worklist",
    "render_worklist_item",
    "filter_worklist",
]
