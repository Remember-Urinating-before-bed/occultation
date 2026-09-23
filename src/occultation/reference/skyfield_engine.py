"""Placeholder for the Skyfield reference engine (milestone 1).

The engine is intentionally unimplemented. It exists now so that the command
line can offer ``--engine skyfield`` and ``--engine compare`` with a stable
interface, and so that the failure mode is explicit and tested.

Milestone 1 will replace the body of :meth:`SkyfieldEngine.star_local_circumstances`
with a real calculation: load ``data/external/de440s.bsp`` by explicit local
path (never downloading at runtime), build a Hong Kong observer, and reduce the
same inputs to a :class:`~occultation.domain.occultation.StarOccultationResult`.

Two rules that will still apply then:

- no import of Skyfield at module import time, so that the custom engine keeps
  working with no reference dependencies installed;
- the custom core must never import this module.
"""

from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    StarOccultationElements,
    StarOccultationResult,
)

#: Message shared by the CLI and the tests, so the wording cannot drift.
UNAVAILABLE_REASON = (
    "the Skyfield reference engine is not implemented yet: milestone 1 needs a "
    "local JPL ephemeris (data/manifest.json currently declares zero datasets)"
)


class ReferenceEngineUnavailable(RuntimeError):
    """Raised when a reference calculation is requested but cannot be performed."""


class SkyfieldEngine:
    """A stand-in for the Skyfield-backed reference engine.

    The constructor takes no arguments yet. Milestone 1 will add the ephemeris
    path and the engine version, which is why the class exists rather than a
    bare function.
    """

    name = "skyfield"

    def star_local_circumstances(
        self,
        elements: StarOccultationElements,
        observer: ObserverLocation,
        delta_t_seconds: float,
    ) -> StarOccultationResult:
        """Raise :class:`ReferenceEngineUnavailable`; never return a number."""
        del elements, observer, delta_t_seconds
        raise ReferenceEngineUnavailable(UNAVAILABLE_REASON)
