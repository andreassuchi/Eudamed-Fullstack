"""Parse an EUDAMED DTX response (Acknowledgement / PullResponse) message.

The response carries a per-entity result: entityCode (the natural key of the
Basic UDI-DI or UDI-DI) and responseCode (see RESPONSE_CODES). Parsing is
namespace-agnostic and lenient — it never validates against the XSD, so real
responses that vary slightly are still read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from lxml import etree

# service/Message MessageType.xsd :: ProcessStatusCodeEnum
SUCCESS_CODE = "SUCCESS"
RESPONSE_CODES = {
    "SUCCESS", "BAD_REQUEST", "CONFLICT", "PROCESSED_WITH_ERRORS",
    "SECURITY_ERROR", "SERVER_ERROR", "UNAUTHORISED_ERROR",
    "INVALID_REQUEST_OBJECTS", "SERVICE_NOT_FOUND",
}


@dataclass
class ResponseEntity:
    entity_code: str
    response_code: str
    messages: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.response_code == SUCCESS_CODE


@dataclass
class ParsedResponse:
    entities: List[ResponseEntity] = field(default_factory=list)
    creation_datetime: Optional[str] = None
    top_response_code: Optional[str] = None

    @property
    def is_response(self) -> bool:
        """A recognisable EUDAMED response (has entity results or a top code)."""
        return bool(self.entities) or self.top_response_code is not None


def _localname(el) -> str:
    return etree.QName(el).localname


def parse_response(source: Union[bytes, str, Path]) -> ParsedResponse:
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        root = etree.parse(str(source)).getroot()
    elif isinstance(source, bytes):
        root = etree.fromstring(source)
    else:  # raw XML string
        root = etree.fromstring(str(source).encode("utf-8"))

    result = ParsedResponse()
    for el in root.iter():
        ln = _localname(el)
        if ln == "creationDateTime" and el.text and result.creation_datetime is None:
            result.creation_datetime = el.text.strip()
        elif ln == "responseEntity":
            code = rc = None
            messages: List[str] = []
            for child in el.iter():
                cln = _localname(child)
                if cln == "entityCode" and child.text:
                    code = child.text.strip()
                elif cln == "responseCode" and child.text:
                    rc = child.text.strip()
                elif cln in ("operationErrorDetail", "operationErrorCode", "operationDetail") and child.text:
                    messages.append(child.text.strip())
            if code and rc:
                result.entities.append(ResponseEntity(code, rc, messages))

    # top-level responseCode (PullResponse / Acknowledgement summary), if any
    for el in root.iter():
        if _localname(el) == "responseCode" and el.getparent() is root and el.text:
            result.top_response_code = el.text.strip()
            break
    return result
