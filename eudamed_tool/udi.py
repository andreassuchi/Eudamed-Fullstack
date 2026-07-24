"""UDI-DI / Basic UDI-DI check-digit generation and validation.

Per issuing entity:
- GS1  UDI-DI       = GTIN, numeric, mod-10 check digit
- GS1  Basic UDI-DI = GMN, MOD 1021,32 two-character check pair
                      (algorithm + character sets from GS1's official
                       gmn-helpers reference implementation)
- HIBCC UDI-DI / Basic UDI-DI = HIBC LIC primary data, mod-43 (Code 39)
                                check character

Other issuing entities (EUDAMED, IFA, ICCBBA) use different schemes and are
reported as "unsupported" rather than failed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# --- GS1 GTIN (UDI-DI): mod-10 ----------------------------------------------

def gtin_check_digit(payload_without_check: str) -> str:
    """Check digit for a numeric GS1 key given all digits except the check digit."""
    total = 0
    for i, ch in enumerate(reversed(payload_without_check)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    return str((10 - (total % 10)) % 10)


def complete_gtin(payload_without_check: str) -> str:
    return payload_without_check + gtin_check_digit(payload_without_check)


def is_valid_gtin(code: str) -> bool:
    if not code.isdigit() or len(code) < 2 or len(code) > 14:
        return False
    return gtin_check_digit(code[:-1]) == code[-1]


# --- GS1 GMN (Basic UDI-DI): MOD 1021,32 ------------------------------------
# Descending primes; a GMN base is 1..23 chars (first 5 = GS1 Company Prefix).
_GMN_WEIGHTS = [83, 79, 73, 71, 67, 61, 59, 53, 47, 43, 41, 37, 31, 29, 23,
                19, 17, 13, 11, 7, 5, 3, 2]
_CSET82 = ("!\"%&'()*+,-./0123456789:;<=>?ABCDEFGHIJKLMNOPQRSTUVWXYZ"
           "_abcdefghijklmnopqrstuvwxyz")
_CSET32 = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CSET82_INDEX = {c: i for i, c in enumerate(_CSET82)}
_CSET32_SET = set(_CSET32)
_GMN_MIN_BASE = 6   # shortest base that GS1 accepts before the check pair
_GMN_MAX_BASE = len(_GMN_WEIGHTS)  # 23


def _mod1021_32_pair(base: str) -> str:
    """MOD 1021,32 two-character check pair over `base` (shared by the GS1 GMN
    and the HIBCC Basic UDI-DI). Character values from cset82, prime weights,
    output pair from the 32-character depleted set."""
    if not (1 <= len(base) <= _GMN_MAX_BASE):
        raise ValueError(f"check base must be 1..{_GMN_MAX_BASE} characters")
    offset = len(_GMN_WEIGHTS) - len(base)
    total = 0
    for i, ch in enumerate(base):
        if ch not in _CSET82_INDEX:
            raise ValueError(f"invalid character: {ch!r}")
        total += _CSET82_INDEX[ch] * _GMN_WEIGHTS[offset + i]
    total %= 1021
    return _CSET32[total // 32] + _CSET32[total % 32]


def gmn_check_pair(base: str) -> str:
    """Two GS1 GMN check characters for the base (GMN without the check pair)."""
    if not (_GMN_MIN_BASE <= len(base) <= _GMN_MAX_BASE):
        raise ValueError(f"GMN base must be {_GMN_MIN_BASE}..{_GMN_MAX_BASE} characters")
    if not base[:5].isdigit():
        raise ValueError("GMN must start with a 5-digit GS1 Company Prefix")
    return _mod1021_32_pair(base)


def complete_gmn(base: str) -> str:
    return base + gmn_check_pair(base)


def is_valid_gmn(code: str) -> bool:
    if not (_GMN_MIN_BASE + 2 <= len(code) <= _GMN_MAX_BASE + 2):
        return False
    base, checks = code[:-2], code[-2:]
    if set(checks) - _CSET32_SET:
        return False
    try:
        return gmn_check_pair(base) == checks
    except ValueError:
        return False


# --- HIBCC (LIC primary data): mod-43 ---------------------------------------
# Code-39 character set (position == value). The HIBC Supplier Labeling Flag
# "+" is part of the primary data message and IS included in the check sum
# (its value is 41). Verified against the standard worked example:
# "+A123BJC5D6E71" -> sum 145 -> 145 mod 43 = 16 -> "G".
_HIBC_CSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%"
_HIBC_INDEX = {c: i for i, c in enumerate(_HIBC_CSET)}
HIBC_FLAG = "+"


def hibcc_check_char(data: str) -> str:
    """HIBC mod-43 check character over the primary data (excluding the check).

    The "+" flag is included in the sum; it is prepended if the caller omitted
    it, so both "+A123BJC5D6E71" and "A123BJC5D6E71" yield the same check char.
    """
    if not data.startswith(HIBC_FLAG):
        data = HIBC_FLAG + data
    total = 0
    for ch in data.upper():
        if ch not in _HIBC_INDEX:
            raise ValueError(f"invalid HIBC character: {ch!r}")
        total += _HIBC_INDEX[ch]
    return _HIBC_CSET[total % 43]


def complete_hibcc(data: str) -> str:
    return data + hibcc_check_char(data)


def is_valid_hibcc(code: str) -> bool:
    if len(code) < 2:
        return False
    try:
        return hibcc_check_char(code[:-1]) == code[-1].upper()
    except ValueError:
        return False


# --- HIBCC Basic UDI-DI: MOD 1021,32 (same core as the GS1 GMN) --------------
# Structure: "++" flag + LIC (4) + Model Identifier (1..17) + 2 check chars.
# The "++" flag is part of the message and included in the sum. Verified against
# the HIBCC example "++A999MODELIDENTIFIER11" -> 774 -> "S8".
HIBC_BASIC_FLAG = "++"


def _hibcc_basic_base(base: str) -> str:
    return base if base.startswith(HIBC_BASIC_FLAG) else HIBC_BASIC_FLAG + base.lstrip("+")


def hibcc_basic_check_pair(base: str) -> str:
    return _mod1021_32_pair(_hibcc_basic_base(base))


def complete_hibcc_basic(base: str) -> str:
    full_base = _hibcc_basic_base(base)
    return full_base + hibcc_basic_check_pair(full_base)


def is_valid_hibcc_basic(code: str) -> bool:
    if len(code) < 3:
        return False
    base, checks = code[:-2], code[-2:]
    if set(checks) - _CSET32_SET:
        return False
    try:
        return hibcc_basic_check_pair(base) == checks
    except ValueError:
        return False


# --- dispatch by issuing entity ---------------------------------------------

@dataclass
class UdiCheck:
    supported: bool          # False for entities with no implemented scheme
    valid: Optional[bool]    # None when unsupported
    scheme: str              # "GTIN" | "GMN" | "HIBC" | "HIBC-BASIC" | "unsupported"
    corrected: Optional[str] = None  # full code with the correct check digit(s)
    message: str = ""


def _scheme_for(issuing_entity: str, is_basic: bool) -> Optional[str]:
    ie = (issuing_entity or "").upper()
    if ie == "GS1":
        return "GMN" if is_basic else "GTIN"
    if ie == "HIBCC":
        return "HIBC-BASIC" if is_basic else "HIBC"
    return None


def validate_di(code: str, issuing_entity: str, *, is_basic: bool) -> UdiCheck:
    """Validate a DI code and, when the check digit is wrong, offer a corrected code."""
    code = (code or "").strip()
    scheme = _scheme_for(issuing_entity, is_basic)
    if scheme is None:
        return UdiCheck(False, None, "unsupported",
                        message=f"No check-digit scheme for issuing entity {issuing_entity!r}.")
    try:
        if scheme == "GTIN":
            valid = is_valid_gtin(code)
            corrected = complete_gtin(code[:-1]) if (len(code) >= 2 and code.isdigit()) else None
        elif scheme == "GMN":
            valid = is_valid_gmn(code)
            corrected = complete_gmn(code[:-2]) if len(code) >= _GMN_MIN_BASE + 2 else None
        elif scheme == "HIBC-BASIC":
            valid = is_valid_hibcc_basic(code)
            corrected = complete_hibcc_basic(code[:-2]) if len(code) >= 3 else None
        else:  # HIBC (UDI-DI, mod-43)
            valid = is_valid_hibcc(code)
            corrected = complete_hibcc(code[:-1]) if len(code) >= 2 else None
    except ValueError as exc:
        return UdiCheck(True, False, scheme, message=str(exc))
    if valid:
        return UdiCheck(True, True, scheme, corrected=code, message=f"Valid {scheme} check digit.")
    msg = f"{scheme} check digit is incorrect."
    if corrected:
        msg += f" Correct code: {corrected}"
    return UdiCheck(True, False, scheme, corrected=corrected, message=msg)


def complete_di(base: str, issuing_entity: str, *, is_basic: bool) -> str:
    """Append the correct check digit(s) to a base code (without check digits)."""
    base = (base or "").strip()
    scheme = _scheme_for(issuing_entity, is_basic)
    if scheme == "GTIN":
        return complete_gtin(base)
    if scheme == "GMN":
        return complete_gmn(base)
    if scheme == "HIBC-BASIC":
        return complete_hibcc_basic(base)
    if scheme == "HIBC":
        return complete_hibcc(base)
    raise ValueError(f"No check-digit scheme for issuing entity {issuing_entity!r}")
