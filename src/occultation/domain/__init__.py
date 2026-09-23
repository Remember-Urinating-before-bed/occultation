"""Package holding the project's domain value objects.

The value objects are frozen, validated, and name their units and time scales
explicitly (``longitude_deg_east``, ``reference_hour_td``,
``separation_in_moon_radii``). They contain no astronomy: only the shape of the
data and the checks that reject impossible values.
"""
