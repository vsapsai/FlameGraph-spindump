#!/usr/bin/env python

import unittest
import flamegraph

class TakeUntilEmptyLineTestCase(unittest.TestCase):
    def test_trivial(self):
        first, rest = flamegraph.take_until_empty_line(["a", "", "b", "c"])
        self.assertEqual(first, ["a"])
        self.assertEqual(rest, ["b", "c"])

    def test_no_rest(self):
        first, rest = flamegraph.take_until_empty_line(["a", "b"])
        self.assertEqual(first, ["a", "b"])
        self.assertIsNone(rest)

    def test_single_line(self):
        first, rest = flamegraph.take_until_empty_line(["a"])
        self.assertEqual(first, ["a"])
        self.assertIsNone(rest)

    def test_few_empty_lines(self):
        first, rest = flamegraph.take_until_empty_line(["a", "", "", "", "b", "c"])
        self.assertEqual(first, ["a"])
        self.assertEqual(rest, ["b", "c"])

    def test_ends_with_empty_line(self):
        first, rest = flamegraph.take_until_empty_line(["a", "b", ""])
        self.assertEqual(first, ["a", "b"])
        self.assertIsNone(rest)

class SplitOnColonTestCase(unittest.TestCase):
    def test_trivial(self):
        actual = flamegraph.split_on_colon(["a: b"])
        self.assertEqual(actual, [("a", "b")])

    def test_real_example(self):
        actual = flamegraph.split_on_colon([
            "PID:             55811",
            "Event:           hang"])
        self.assertEqual(actual, [("PID", "55811"), ("Event", "hang")])

if __name__ == '__main__':
    unittest.main()
