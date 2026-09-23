"""Package holding input/output adapters: files in, domain values out.

Nothing here performs astronomy. These modules only translate a stored or
supplied representation (JSON, TOML, a command-line mapping) into the frozen
domain objects in :mod:`occultation.domain`, so that the calculation core stays
independent of where its inputs came from.

The custom core (``occultation.core``) must never import this package, and this
package must never import ``occultation.reference``.
"""
