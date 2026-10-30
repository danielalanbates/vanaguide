# Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
"""Synthetic geometry only; no proprietary data or live clients."""
import unittest
from gen_navgrid import rasterise, inside

class GridCenters(unittest.TestCase):
    def test_triangle_boundary_is_not_walkable_in_center_mode(self):
        ring = [(0, 0, 0), (4, 0, 0), (0, 4, 0)]
        legacy = rasterise([ring], 2, 1000, 2)
        strict = rasterise([ring], 2, 1000, 2, True)
        self.assertLess(sum(strict[5]), sum(legacy[5]))
        ox, oz, w, h, cell, mask, *_ = strict
        for i, occupied in enumerate(mask):
            if occupied:
                self.assertTrue(inside(ring, ox + (i % w + .5) * cell, oz + (i // w + .5) * cell))

    def test_open_interior_remains(self):
        square = [(0, 0, 0), (8, 0, 0), (8, 8, 0), (0, 8, 0)]
        grid = rasterise([square], 2, 1000, 2, True)
        self.assertGreaterEqual(sum(grid[5]), 16)

    def test_subcell_sliver_does_not_invent_a_floor(self):
        sliver = [(0, 0, 0), (.1, 0, 0), (0, .1, 0)]
        self.assertGreater(sum(rasterise([sliver], 2, 1000, 2)[5]), 0)
        self.assertEqual(sum(rasterise([sliver], 2, 1000, 2, True)[5]), 0)

if __name__ == '__main__': unittest.main()
