"""Create a random starting board for Settlers of Catan.

TODO: Center the board using a bounding box
TODO: Draw the sea tiles, and allow them to be randomized
TODO: Left align checkbox text
TODO: Control size adjustment with resizing of window
TODO: Simplify the algorithm for red placement now there is a connected path through
      the graph that visits every node.
TODO: Docstrings and unittests.
TODO: Images and patterns
"""

from typing import Dict, Iterable, Sequence
import collections
import functools
import itertools
import math
import random
import tkinter
import unittest


random.seed()


class TkinterOptionWrapper:

    """Dynamically hook up the board options to tkinter checkbuttons.

    Tkinter checkbuttons use a tkinter 'var' object to store the checkbutton
    value, so dynamically create those vars based on the board options and
    keep them here, along with callbacks to update the board options when the
    checkbutton is checked/unchecked.

    Also stores the option description text. That should probably belong to the
    board option 'class', but at the moment there's no reason not to keep that
    a simple dict.

    Parameters
    ----------

    options : A dict of option identifier (name) to option value

    The wrapper will dynamically update the value of the option in the
    option_dict when the user checks or unchecks the corresponding checkbutton
    in the UI.
    """

    Option = collections.namedtuple('_Option', ['text', 'var', 'callback'])
    _descriptions = {
        'randomize_ports':      'Randomize port types',
        'randomize_production': 'Randomize hex values'}

    def __init__(self, option_dict):
        self._opts = {}

        # Can't define this as a closure inside the following for loop as each
        # definition will become the value of cb which has a scope local to the
        # function, not to the for loop.  Use functools.partial in the loop to
        # create a specific callable instance.
        def cb_template(name, var):
            option_dict[name] = var.get()

        for name, value in option_dict.items():
            var = tkinter.BooleanVar()
            var.set(value)
            cb = functools.partial(cb_template, name, var)
            self._opts[name] = self.Option(self._descriptions[name], var, cb)

    def __getattr__(self, name):
        attr = self.__dict__.get(name)
        if '_opts' in self.__dict__ and not attr:
            attr = self._opts.get(name)
        return attr

    def __iter__(self):
        for opt in self._opts.values():
            yield opt


class BoardUI(tkinter.Frame):

    def __init__(self, master, options, *args, **kwargs):
        super(BoardUI, self).__init__(master, *args, **kwargs)
        self.options = options

        canvas = tkinter.Canvas(self, height=600, width=600, background='Royal Blue')
        button = tkinter.Button(self, text='New', command=self.redraw)

        cb_frame = tkinter.Frame(self)
        for option in TkinterOptionWrapper(options):
            option.callback()
            tkinter.Checkbutton(cb_frame,
                                text = option.text,
                                command = option.callback,
                                var = option.var) \
                   .pack(side=tkinter.TOP, fill=tkinter.X)
        cb_frame.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        canvas.pack(side=tkinter.TOP, expand=tkinter.YES, fill=tkinter.BOTH)
        button.pack(side=tkinter.BOTTOM, expand=tkinter.YES, fill=tkinter.X)

        self._canvas = canvas
        self._button = button
        self._center_to_edge = math.cos(math.radians(30)) * self._tile_radius

    def draw(self, board):

        """Render the board to the canvas widget.

        Taking the center of the first tile as 0, 0 we follow the path of tiles
        around the graph as given by the board (must be guaranteed to be a
        connected path that visits every tile) and calculate the center of each
        tile as the offset from the last one, based on it's direction from the
        last tile and the radius of the hexagons (and padding etc.)

        We then shift all the individual tile centers so that the board center
        is at 0, 0.
        """

        centers = {}
        last = None

        for tile in board.tiles:
            if not last:
                centers[tile.id] = (0, 0)
                last = tile
                continue

            # Calculate the center of this tile as an offset from the center of
            # the neighboring tile in the given direction.
            ref_center = centers[last.id]
            direction = board.direction(last, tile)
            theta = self._angle_order.index(direction) * 60
            radius = 2 * self._center_to_edge + self._tile_padding
            dx = radius * math.cos(math.radians(theta))
            dy = radius * math.sin(math.radians(theta))
            centers[tile.id] = (ref_center[0] + dx, ref_center[1] + dy)
            last = tile

        port_centers = []
        for tile_id, dirn, value in board.ports:
            ref_center = centers[tile_id]
            theta = self._angle_order.index(dirn) * 60
            radius = 2 * self._center_to_edge + self._tile_padding
            dx = radius * math.cos(math.radians(theta))
            dy = radius * math.sin(math.radians(theta))
            port_centers.append((ref_center[0] + dx, ref_center[1] + dy, theta))

        offx, offy = self._board_center

        # Temporary hack to center the board. Not generic to different board types.
        radius = 4 * self._center_to_edge + 2 * self._tile_padding
        offx += radius * math.cos(math.radians(240))
        offy += radius * math.sin(math.radians(240))

        centers = dict((tile_id, (x + offx, y + offy)) for tile_id, (x, y) in centers.items())
        for tile_id, (x, y) in centers.items():
            tile = board.tiles[tile_id - 1]
            self._draw_tile(x, y, tile.terrain, tile.value)

        port_centers = [(x + offx, y + offy, t + 180) for x, y, t in port_centers]
        for (x, y, t), value in zip(port_centers, [v for _, _, v in board.ports]):
            self._draw_port(x, y, t, value)

    def redraw(self):
        self._canvas.delete(tkinter.ALL)
        self.draw(Board(self.options))

    def _draw_hexagon(self, radius, offset=(0, 0), rotate=30, fill='black'):
        points = hex_points(radius, offset, rotate)
        self._canvas.create_polygon(*itertools.chain.from_iterable(points), fill=fill)

    def _draw_tile(self, x, y, terrain, value):
        self._draw_hexagon(self._tile_radius, offset=(x, y), fill=self._colors[terrain])
        if value:
            color = 'red' if value in (6, 8) else 'black'
            self._canvas.create_text(x, y, text=str(value), font=self._hex_font, fill=color)

    def _draw_port(self, x, y, angle, value):
        """Draw a equilateral triangle with the top point at x, y and the bottom
        facing the direction given by the angle.
        """
        points = [x, y]
        for adjust in (-30, 30):
            x1 = x + math.cos(math.radians(angle + adjust)) * self._tile_radius
            y1 = y + math.sin(math.radians(angle + adjust)) * self._tile_radius
            points.extend([x1, y1])
        self._canvas.create_polygon(*points, fill=self._colors[value])
        self._canvas.create_text(x, y, text=value, font=self._hex_font)

    _tile_radius  = 50
    _tile_padding = 3
    _board_center = (300, 300)
    _angle_order  = ('E', 'SE', 'SW', 'W', 'NW', 'NE')
    _hex_font     = (('Sans'), 18)
    _colors = {
        'M': 'gray94',
        'O': 'gray94',
        'F': 'forest green',
        'L': 'forest green',
        'P': 'green yellow',
        'W': 'green yellow',  # wool
        'C': 'sienna4',
        'B': 'sienna4',
        'H': 'wheat1',  # wheat
        'G': 'wheat1',
        'D': 'yellow2',
        '?': 'gray'}


Tile = collections.namedtuple('Tile', ['id', 'terrain', 'value'])


class Board:

    """Represents a single starting game board.

    Encapsulates the layout of the board (which tiles are connected to which),
    and the values of the tiles (including ports).

    Board.tiles() returns an iterable that gives the tiles in a guaranteed
    connected path that covers every node in the board graph.

    Board.direction(from, to) gives the compass direction you need to take to
    get from the origin tile to the destination tile.
    """

    def __init__(self, options: Dict[str, bool], tiles=None, graph=None, center=1) -> None:
        """
        options is a dict names to boolean values.
        tiles and graph are for passing in a pre-defined set of tiles or a
        different graph for testing purposes.
        """
        self.options = options
        self.tiles = tiles or self._generate()  # type: Sequence[Tile]
        self.center_tile = self.tiles[center or 10]
        if graph:
            self._graph = graph

    def direction(self, src: Tile, dst: Tile) -> str:
        return next(e[2] for e in self._edges_for(src)
                               if e[1] == dst.id)

    def neighbors_for(self, tile):
        return [self.tiles[e[1] - 1] for e in self._edges_for(tile)]

    def _generate(self):
        while True:
            terrain = list(self._terrain)
            numbers = list(self._numbers)
            ports   = list(self._ports)

            random.shuffle(terrain)
            if self.options['randomize_production']:
                random.shuffle(numbers)
            if self.options['randomize_ports']:
                random.shuffle(ports)

            self.ports = [(tile, dir, value) for (tile, dir), value in zip(self._port_locations, ports)]
            tile_data = list(zip(terrain, numbers))
            tile_data.insert(random.randrange(len(tile_data) + 1), ('D', None))
            if self.options['randomize_production'] and not self._check_red_placement(tile_data):
                continue
            return [Tile(id=i, terrain=t, value=v) for i, (t, v) in enumerate(tile_data, 1)]

    def _check_red_placement(self, tiles):
        for i1, i2, _ in self._graph:
            t1 = tiles[i1 - 1]
            t2 = tiles[i2 - 1]
            if all(t[1] in (6, 8) for t in [t1, t2]):
                return False
        return True

    def _edges_for(self, tile):
        return [e         for e in self._graph if e[0] == tile.id] + \
               [invert(e) for e in self._graph if e[1] == tile.id]

    _terrain = (['F'] * 4 + ['P'] * 4 + ['H'] * 4 + ['M'] * 3 + ['C'] * 3)
    _numbers = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
    _ports   = ['?', 'O', 'G', '?', 'L', 'B', '?', '?', 'W']
    # Ore, Wool, Grain, Lumber, Brick
    _graph = [(1,  2,  'SW'), (1,  12, 'E' ), (1,  13, 'SE'),
              (2,  3,  'SW'), (2,  13, 'E' ), (2,  14, 'SE'),
              (3,  4,  'SE'), (3,  14, 'E' ),
              (4,  5,  'SE'), (4,  14, 'NE'), (4,  15, 'E' ),
              (5,  6,  'E' ), (5,  15, 'NE'),
              (6,  7,  'E' ), (6,  15, 'NW'), (6,  16, 'NE'),
              (7,  8,  'NE'), (7,  16, 'NW'),
              (8,  9,  'NE'), (8,  16, 'W' ), (8,  17, 'NW'),
              (9,  10, 'NW'), (9,  17, 'W' ),
              (10, 11, 'NW'), (10, 17, 'SW'), (10, 18, 'W' ),
              (11, 12, 'W' ), (11, 18, 'SW'),
              (12, 13, 'SW'), (12, 18, 'SE'),
              (13, 14, 'SW'), (13, 18, 'E' ), (13, 19, 'SE'),
              (14, 15, 'SE'), (14, 19, 'E' ),
              (15, 16, 'E' ), (15, 19, 'NE'),
              (16, 17, 'NE'), (16, 19, 'NW'),
              (17, 18, 'NW'), (17, 19, 'W' ),
              (18, 19, 'SW')]
    _port_locations = [(1, 'NW'), (2,  'W'),  (4,  'W' ),
                       (5, 'SW'), (6,  'SE'), (8,  'SE'),
                       (9, 'E' ), (10, 'NE'), (12, 'NE')]

_direction_pairs = {
    'E': 'W', 'SW': 'NE', 'SE': 'NW',
    'W': 'E', 'NE': 'SW', 'NW': 'SE'}


def invert(edge):
    return (edge[1], edge[0], _direction_pairs[edge[2]])


def hex_points(radius, offset, rotate):
    offx, offy = offset
    points = []
    for theta in (60 * n for n in range(6)):
        x = (math.cos(math.radians(theta + rotate)) * radius) + offx
        y = (math.sin(math.radians(theta + rotate)) * radius) + offy
        points.append((x, y))
    return points


def main():
    root = tkinter.Tk()
    root.lift()
    options = {
        'randomize_production': True,
        'randomize_ports': True}
    ui = BoardUI(root, options)
    ui.pack()
    ui.draw(Board(options))
    root.mainloop()


if __name__ == "__main__":
    main()
