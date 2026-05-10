"""Cian integration placeholder.

Discovery checklist (run from a host with RU access, see DEVELOPMENT_PLAN.md section 0.E):
- Reachability of listing/search endpoints and ToS constraints.
- Stable fields: price, area, location text, offer id if exposed in HTML/JSON.

Next step after recon: implement fetch + normalize into app.models.MarketComparable rows linked by lot_id.
"""


async def fetch_cian_comparables_for_lot(_lot_id: int) -> list[dict]:
    """Not implemented — returns empty list until official API or approved scraping path exists."""
    return []
