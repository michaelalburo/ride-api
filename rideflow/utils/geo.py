from django.db.models import F, FloatField, Value
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin

EARTH_RADIUS_KM = 6371.0


def distance_expression(latitude, longitude):
    """Great-circle distance (km) from (latitude, longitude) to each row's pickup point.

    Built entirely from Django's cross-backend math functions (SQLite and
    Postgres both implement ACos/Cos/Sin/Radians natively), so the whole
    computation runs in the database via ORDER BY, never in Python.
    """
    lat_rad = Radians(F('pickup_latitude'))
    lng_rad = Radians(F('pickup_longitude'))
    origin_lat_rad = Radians(Value(latitude, output_field=FloatField()))
    origin_lng_rad = Radians(Value(longitude, output_field=FloatField()))

    central_angle_cos = (
        Sin(origin_lat_rad) * Sin(lat_rad)
        + Cos(origin_lat_rad) * Cos(lat_rad) * Cos(lng_rad - origin_lng_rad)
    )
    # Clamp to [-1, 1]: floating-point rounding can push the cosine of a
    # near-zero angle (i.e. a pickup point very close to the origin) just
    # outside the domain of ACos, which would otherwise raise/return NULL.
    clamped_cos = Least(Value(1.0), Greatest(Value(-1.0), central_angle_cos))
    return EARTH_RADIUS_KM * ACos(clamped_cos)
