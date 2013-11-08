#!/usr/bin/env python

from __future__ import unicode_literals
import unittest
import io
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


class FrameSampleTestCase(unittest.TestCase):
    def test_height(self):
        parent = flamegraph.FrameSample("parent + 1 (Foo) [0x7fff80004444]", 9)
        child_a = flamegraph.FrameSample("child_a + 1 (Foo) [0x7fff80004444]", 3)
        child_b = flamegraph.FrameSample("child_b + 1 (Foo) [0x7fff80004444]", 4)
        grand_child_b = flamegraph.FrameSample("grand_child_b + 1 (Foo) [0x7fff80004444]", 2)
        parent.add_child_sample(child_a)
        parent.add_child_sample(child_b)
        child_b.add_child_sample(grand_child_b)
        self.assertEqual(parent.height(), 3)
        self.assertEqual(child_a.height(), 1)
        self.assertEqual(child_b.height(), 2)
        self.assertEqual(grand_child_b.height(), 1)

    def test_iteritems(self):
        parent = flamegraph.FrameSample("parent + 1 (Foo) [0x7fff80004444]", 9)
        child_a = flamegraph.FrameSample("child_a + 1 (Foo) [0x7fff80004444]", 3)
        child_b = flamegraph.FrameSample("child_b + 1 (Foo) [0x7fff80004444]", 4)
        grand_child_b = flamegraph.FrameSample("grand_child_b + 1 (Foo) [0x7fff80004444]", 2)
        parent.add_child_sample(child_a)
        parent.add_child_sample(child_b)
        child_b.add_child_sample(grand_child_b)
        actual_items = [(frame.frame, start, depth) for frame, start, depth in parent.iteritems()]
        expected_items = [("parent + 1 (Foo) [0x7fff80004444]", 0, 0),
                          ("child_a + 1 (Foo) [0x7fff80004444]", 0, 1),
                          ("child_b + 1 (Foo) [0x7fff80004444]", 3, 1),
                          ("grand_child_b + 1 (Foo) [0x7fff80004444]", 3, 2)]
        self.assertEqual(actual_items, expected_items)


class SVGTestCase(unittest.TestCase):
    def full_svg_dump(self, svg):
        string_buffer = io.StringIO()
        svg.dump(string_buffer)
        result = string_buffer.getvalue()
        string_buffer.close()
        return result

    def short_svg_dump(self, svg):
        full_dump = self.full_svg_dump(svg)
        result = full_dump[full_dump.find('>') + 1:]
        result = result[:result.rfind('<')]
        result = result.strip()
        return result

    def test_empty(self):
        svg = flamegraph.SVG(45, 62)
        actual_svg = self.full_svg_dump(svg)
        expected_svg = """<svg width="45" height="62" viewBox="0 0 45 62"
version="1.1" xmlns="http://www.w3.org/2000/svg">

</svg>"""
        self.assertEqual(expected_svg, actual_svg)

    def test_add_rect(self):
        svg = flamegraph.SVG(100, 100)
        svg.add_rect(23.23, 76.76, 45, 54, 'rgb(100,100,100)')
        actual_svg = self.short_svg_dump(svg)
        expected_svg = '<rect x="23.2" y="76.8" width="45.0" height="54.0" fill="rgb(100,100,100)" rx="2" ry="2" />'
        self.assertEqual(expected_svg, actual_svg)

    def test_add_text(self):
        svg = flamegraph.SVG(100, 100)
        svg.add_text("foo", 12.34, 56.78)
        actual_svg = self.short_svg_dump(svg)
        expected_svg = '<text x="12.3" y="56.8" font-size="12" font-family="Helvetica">foo</text>'
        self.assertEqual(expected_svg, actual_svg)

    def test_escaping_text(self):
        svg = flamegraph.SVG(100, 100)
        svg.add_text("int const&", 12.34, 56.78)
        actual_svg = self.short_svg_dump(svg)
        expected_svg = '<text x="12.3" y="56.8" font-size="12" font-family="Helvetica">int const&amp;</text>'
        self.assertEqual(expected_svg, actual_svg)

    def test_non_ascii_text(self):
        svg = flamegraph.SVG(100, 100)
        svg.add_text("\u2026", 12.34, 56.78)
        actual_svg = self.short_svg_dump(svg)
        expected_svg = '<text x="12.3" y="56.8" font-size="12" font-family="Helvetica">\u2026</text>'
        self.assertEqual(expected_svg, actual_svg)

if __name__ == '__main__':
    unittest.main()
