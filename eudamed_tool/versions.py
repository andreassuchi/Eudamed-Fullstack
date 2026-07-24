"""Target EUDAMED release and DTX schema this build is made for.

Single source of truth — a future release/DTX branch changes these two
constants (and the XSD package under xsd/). XSD_VERSION must match the
`version` attribute fixed by the official Message schema.
"""
from __future__ import annotations

# EUDAMED production release this build targets
EUDAMED_VERSION = "3.31.2"

# DTX data-exchange XSD package version (root Message.xsd fixed attribute)
DTX_SCHEMA_VERSION = "3.0.32"
