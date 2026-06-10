"""Verify a National Provider Identifier against the federal NPPES registry.

NPPES is the official CMS provider directory and exposes a free JSON API (no key). We treat
an NPI as verified when it exists, is active, and the registered name matches the clinician's.
"""
import requests

NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"


def verify_npi(npi, first_name, last_name, *, session=None, timeout=10):
    """Return ``(verified: bool, detail: dict)`` for an NPI lookup.

    verified == the NPI exists, status is active ('A'), and first+last name match
    (case-insensitive). Non-matches (e.g. a nickname) come back False so they route to
    manual review rather than being wrongly auto-verified.
    """
    client = session or requests
    try:
        response = client.get(
            NPPES_API_URL, params={"version": "2.1", "number": npi}, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return False, {"reason": "lookup_failed", "error": str(exc)}

    results = data.get("results") or []
    if not results:
        return False, {"reason": "not_found"}

    basic = results[0].get("basic", {})
    status = basic.get("status")  # 'A' == active
    reg_first = (basic.get("first_name") or "").strip().lower()
    reg_last = (basic.get("last_name") or "").strip().lower()
    name_matches = reg_first == (first_name or "").strip().lower() and reg_last == (last_name or "").strip().lower()

    return (status == "A" and name_matches), {
        "status": status,
        "registered_name": f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip(),
        "credential": basic.get("credential"),
        "name_matches": name_matches,
    }
