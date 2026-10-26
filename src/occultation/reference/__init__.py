"""The reference engine: a trusted third-party calculation kept for comparison.

Boundary rule (``docs/AGENT_HANDOFF.md`` section 3.4): the custom core in
:mod:`occultation.core` must never import this package. This package may import
the custom core, so a comparison layer can run both engines on identical inputs.

The engine is :class:`SkyfieldEngine`, backed by a local JPL ephemeris
(``data/external/de440s.bsp``) and Skyfield. It answers a slightly different
question from the custom core — see the module docstring of
``skyfield_engine`` — and returns :class:`BodyCircumstances`, a separate type,
so a reference answer can never be mistaken for a custom one.
"""

from occultation.reference.skyfield_engine import (
    BODY_TARGETS,
    DEFAULT_EPHEMERIS_PATH,
    MOON_MEAN_RADIUS_KM,
    UNAVAILABLE_REASON,
    BodyCircumstances,
    ReferenceEngineError,
    ReferenceEngineUnavailable,
    SkyfieldEngine,
)

__all__ = [
    "BODY_TARGETS",
    "DEFAULT_EPHEMERIS_PATH",
    "MOON_MEAN_RADIUS_KM",
    "UNAVAILABLE_REASON",
    "BodyCircumstances",
    "ReferenceEngineError",
    "ReferenceEngineUnavailable",
    "SkyfieldEngine",
]
