# # smoothing.py

# from geoutils import haversine

# def perpendicular_distance(point, line_start, line_end):
#     """
#     Approximate perpendicular distance (km) using triangle area method
#     """
#     if line_start == line_end:
#         return haversine(point, line_start)

#     a = haversine(line_start, line_end)
#     b = haversine(line_start, point)
#     c = haversine(point, line_end)

#     # Heron's formula for triangle area
#     s = (a + b + c) / 2
#     area = max(s * (s - a) * (s - b) * (s - c), 0) ** 0.5

#     # Height = 2 * area / base
#     return (2 * area) / a if a != 0 else 0


# def douglas_peucker(points, epsilon_km):
#     """
#     Simplify a route using Douglas–Peucker algorithm

#     points      : list of (lat, lon)
#     epsilon_km  : tolerance in kilometers
#     """
#     if len(points) < 3:
#         return points

#     max_dist = 0.0
#     index = 0

#     for i in range(1, len(points) - 1):
#         d = perpendicular_distance(points[i], points[0], points[-1])
#         if d > max_dist:
#             max_dist = d
#             index = i

#     if max_dist > epsilon_km:
#         left = douglas_peucker(points[: index + 1], epsilon_km)
#         right = douglas_peucker(points[index:], epsilon_km)
#         return left[:-1] + right
#     else:
#         return [points[0], points[-1]]

#----------------------------

# smoothing.py

from geoutils import haversine
import math

# =========================================================
# BASIC GEOMETRY
# =========================================================

def bearing(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])

    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - \
        math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    return math.degrees(math.atan2(x, y))


def perpendicular_distance(point, line_start, line_end):
    """
    Approximate perpendicular distance (km) using triangle area
    """
    if line_start == line_end:
        return haversine(point, line_start)

    a = haversine(line_start, line_end)
    b = haversine(line_start, point)
    c = haversine(point, line_end)

    s = (a + b + c) / 2
    area = max(s * (s - a) * (s - b) * (s - c), 0) ** 0.5

    return (2 * area) / a if a != 0 else 0


# =========================================================
# DOUGLAS–PEUCKER SIMPLIFICATION
# =========================================================

def douglas_peucker(points, epsilon_km):
    if len(points) < 3:
        return points

    max_dist = 0.0
    index = 0

    for i in range(1, len(points) - 1):
        d = perpendicular_distance(points[i], points[0], points[-1])
        if d > max_dist:
            max_dist = d
            index = i

    if max_dist > epsilon_km:
        left = douglas_peucker(points[: index + 1], epsilon_km)
        right = douglas_peucker(points[index:], epsilon_km)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


# =========================================================
# DENSIFICATION (CRITICAL FOR 0.25° GRID)
# =========================================================

def densify_path(points, step_km=8):
    """
    Adds intermediate points along segments
    WITHOUT changing route geometry
    """
    dense = [points[0]]

    for i in range(len(points) - 1):
        a = points[i]
        b = points[i + 1]
        dist = haversine(a, b)

        if dist <= step_km:
            dense.append(b)
            continue

        steps = int(dist // step_km)

        for s in range(1, steps + 1):
            t = s / (steps + 1)
            dense.append((
                a[0] + t * (b[0] - a[0]),
                a[1] + t * (b[1] - a[1])
            ))

        dense.append(b)

    return dense


# =========================================================
# SAFE SMOOTHING (NO SHORTCUTS)
# =========================================================

def smooth_path(points, max_shift_km=10, angle_threshold=25):
    """
    Gently smooths zig-zags while preserving topology
    """
    if len(points) < 3:
        return points

    smoothed = [points[0]]

    for i in range(1, len(points) - 1):
        prev_pt = points[i - 1]
        curr_pt = points[i]
        next_pt = points[i + 1]

        b1 = bearing(prev_pt, curr_pt)
        b2 = bearing(curr_pt, next_pt)
        turn = abs((b2 - b1 + 180) % 360 - 180)

        # Only smooth sharp turns
        if turn < angle_threshold:
            smoothed.append(curr_pt)
            continue

        candidate = (
            (prev_pt[0] + curr_pt[0] + next_pt[0]) / 3,
            (prev_pt[1] + curr_pt[1] + next_pt[1]) / 3
        )

        # Safety: do not move point too far
        if haversine(curr_pt, candidate) <= max_shift_km:
            smoothed.append(candidate)
        else:
            smoothed.append(curr_pt)

    smoothed.append(points[-1])
    return smoothed


# =========================================================
# FINAL PIPELINE (USE THIS)
# =========================================================

def smooth_route(
    raw_points,
    grid_deg=0.25,
):
    """
    Full smoothing pipeline for coarse maritime grids
    """

    # Approx grid size in km
    grid_km = grid_deg * 111

    # 1️⃣ Simplify initial A* noise
    simplified = douglas_peucker(
        raw_points,
        epsilon_km=0.6 * grid_km
    )

    # 2️⃣ Densify so curves are possible
    dense = densify_path(
        simplified,
        step_km=0.25 * grid_km
    )

    # 3️⃣ Smooth geometry safely
    smooth = smooth_path(
        dense,
        max_shift_km=0.35 * grid_km,
        angle_threshold=25
    )

    # 4️⃣ Optional final cleanup
    # final = douglas_peucker(
    #     smooth,
    #     epsilon_km=0.25 * grid_km
    # )

    return smooth

