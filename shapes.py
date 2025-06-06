from math import pi, sin, cos, radians, sqrt

def create_bean_shape(canvas, cx, cy, cw, ch, steps=10, rotation_deg=0, **kwargs):
    """
    draws a 'bean' shape for X and Y buttons
    taken from https://math.stackexchange.com/a/4642743
    """
    points = []
    for i in range(steps + 1):
        t = 2 * pi * i / steps
        x = 3 + 2 * sin(t) + cos(2 * t)
        y = 4 * cos(t) - sin(2 * t)
        points.append((x, y))

    # normalise and scale to [0, cw] x [0, ch]
    xs, ys = zip(*points)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    scale_x = cw / (max_x - min_x)
    scale_y = ch / (max_y - min_y)

    # angle in radians for rotation
    angle_rad = radians(rotation_deg)

    final_points = []
    for x, y in points:
        # normalise
        nx = (x - min_x) * scale_x - cw / 2
        ny = (y - min_y) * scale_y - ch / 2

        # rotate
        rx = nx * cos(angle_rad) - ny * sin(angle_rad)
        ry = nx * sin(angle_rad) + ny * cos(angle_rad)

        # translate to center
        final_points.extend((cx + rx, cy + ry))

    return canvas.create_polygon(final_points, smooth=True, **kwargs)

def create_semi_circle(canvas, cx, cy, cw=100, ch=50, rotation_deg=0,
                       direction="top", steps=10, **kwargs):
    """
    draws a semicircle with rotation controls
    """
    angle_rad = radians(rotation_deg)
    radius_x = cw / 2
    radius_y = ch / 2

    # angle range for top or bottom arc
    if direction == "top":
        angle_start = pi
        angle_end = 0
    else: # bottom
        angle_start = 0
        angle_end = pi

    arc_points = []
    for i in range(steps + 1):
        theta = angle_start + (angle_end - angle_start) * i / steps
        x = radius_x * cos(theta)
        y = radius_y * sin(theta)

        # rotate around (0,0)
        x_rot = x * cos(angle_rad) - y * sin(angle_rad)
        y_rot = x * sin(angle_rad) + y * cos(angle_rad)

        # translate to center
        arc_points.append((cx + x_rot, cy + y_rot))

    # close the semicircle back to center
    arc_points.append((cx, cy))

    return canvas.create_polygon(arc_points, smooth=True, **kwargs)

def create_triangle(canvas, cx, cy, cw=100, rotation_deg=0, **kwargs):
    """
    draws an equilateral triangle centered at (cx, cy) and can be rotated
    """
    height = (sqrt(3) / 2) * cw

    # define points so the centroid is at (0, 0)
    p1 = (0, -height * 2 / 3)  # top
    p2 = (-cw / 2, height / 3) # bottom left
    p3 = (cw / 2, height / 3)  # bottom right

    angle_rad = radians(rotation_deg)

    def rotate_and_translate(x, y):
        # rotate point
        x_rot = x * cos(angle_rad) - y * sin(angle_rad)
        y_rot = x * sin(angle_rad) + y * cos(angle_rad)
        # translate to center
        return (cx + x_rot, cy + y_rot)

    # apply transform
    points = [rotate_and_translate(*p) for p in (p1, p2, p3)]

    return canvas.create_polygon(points, **kwargs)
