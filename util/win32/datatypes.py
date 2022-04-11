class Point:
    __slots__ = ("x", "y", "rgb")

    def __init__(self, x, y, rgb=None):
        self.x = x
        self.y = y
        self.rgb = rgb

    def __iter__(self):
        return iter((self.x, self.y))


class Rect:
    __slots__ = ("left", "top", "right", "bottom", "width", "height", "center")

    def __init__(self, left=None, top=None, right=None, bottom=None, left_top=None, right_bottom=None):
        if left_top is not None:
            self.left, self.top = left_top
        else:
            self.left = left
            self.top = top

        if right_bottom is not None:
            self.right, self.bottom = right_bottom
        else:
            self.right = right
            self.bottom = bottom

        self.width = self.right - self.left
        self.height = self.bottom - self.top
        self.center = Point(self.left + self.width // 2, self.top + self.height // 2)

    def __iter__(self):
        return iter((self.left, self.top, self.right, self.bottom))

    def __repr__(self):
        return f"Left: {self.left}, Top: {self.top}, Right: {self.right}, Bottom: {self.bottom}"
