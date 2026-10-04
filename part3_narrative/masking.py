"""Masking policy for any narrative that could reach an external-facing summary.

Raw reseller names must never appear; resellers are referenced only by
region and a coded alias.
"""


def alias_for(reseller_id: str) -> str:
    """RS019 -> 'ALIAS-19', RS006 -> 'ALIAS-06'."""
    return f"ALIAS-{reseller_id[3:]}"


def assert_no_raw_names_leak(text: str, reseller_names: list[str]) -> bool:
    """Return False if any raw reseller_name appears verbatim inside text, else True.

    Matching is an exact, case-sensitive substring test. Blank names are
    ignored (an empty string is a substring of every text).
    """
    for name in reseller_names:
        if name and name in text:
            return False
    return True
