"""The reference engine: a trusted third-party calculation kept for comparison.

Boundary rule (``docs/AGENT_HANDOFF.md`` section 3.4): the custom core in
:mod:`occultation.core` must never import this package. This package may import
the custom core, so that a comparison layer can run both engines on identical
inputs.

Today this package contains no working engine. Milestone 1 adds Skyfield plus a
local JPL ephemeris; until then the placeholder raises
:class:`ReferenceEngineUnavailable` rather than returning a number, because
labelling a custom-core result as a reference result would be worse than
failing.
"""

from occultation.reference.skyfield_engine import (
    ReferenceEngineUnavailable,
    SkyfieldEngine,
)

__all__ = ["ReferenceEngineUnavailable", "SkyfieldEngine"]
