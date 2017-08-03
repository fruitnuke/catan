from main import Board
import collections
import unittest


class ClassicBoardTests(unittest.TestCase):

    def test_tile_iterator(self):
        options = {
            'randomize_production': False,
            'randomize_ports': False}
        board = Board(options)
        self.assertEqual([t.value for t in board.tiles if t.value], board._numbers)
        hexes = collections.Counter([t.terrain for t in board.tiles])
        self.assertEqual(hexes['F'], 4)
        self.assertEqual(hexes['P'], 4)
        self.assertEqual(hexes['H'], 4)
        self.assertEqual(hexes['M'], 3)
        self.assertEqual(hexes['C'], 3)
        self.assertEqual(hexes['D'], 1)


if __name__ == '__main__':
    unittest.main()
