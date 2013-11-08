#!/usr/bin/env python

from __future__ import unicode_literals
import operator
import random
import re
import sys
from xml.sax import saxutils


class FrameSample:
    """Represents sampling results for a single frame within a thread trace."""
    def __init__(self, frame, sample_count):
        self.frame = frame
        self.sample_count = sample_count
        self.child_samples = []

    def add_child_sample(self, child_sample):
        self.child_samples.append(child_sample)

    def height(self):
        """Returns distance from current node to the most distant leaf node.

        If self is leaf node returns 1."""
        if len(self.child_samples) > 0:
            child_heights = [child.height() for child in self.child_samples]
            return max(child_heights) + 1
        else:
            return 1

    def iteritems(self):
        """Iterates through all samples (first parent frame, then child frames).

        Yields frame itself, its start and depth."""
        return self.__items_generator(0, 0)

    def __items_generator(self, start, depth):
        yield (self, start, depth)
        child_start = start
        for child_frame in self.child_samples:
            for t in child_frame.__items_generator(child_start, depth + 1):
                yield t
            child_start += child_frame.sample_count


class ThreadTrace:
    _INDENTATION = 2
    _DIGIT_RE = re.compile(r"\d+")

    def __init__(self, trace_lines):
        self.description = trace_lines[0].strip()
        self.root_frame = None
        stack = []
        for trace_line in trace_lines[1:]:
            digit_match = self._DIGIT_RE.search(trace_line)
            assert digit_match is not None
            indentation = digit_match.start()
            assert (indentation % self._INDENTATION) == 0, "Unexpected indentation in line %s" % trace_line
            nested_level = indentation / self._INDENTATION
            if len(stack) >= nested_level:
                # Shorten stack to appropriate level
                stack = stack[:nested_level - 1]
            sample_count = int(trace_line[digit_match.start():digit_match.end()])
            frame = trace_line[digit_match.end() + 1:]
            frame_sample = FrameSample(frame, sample_count)
            if len(stack) > 0:
                stack[-1].add_child_sample(frame_sample)
            else:
                assert self.root_frame is None
                self.root_frame = frame_sample
            stack.append(frame_sample)

    def max_stack_depth(self):
        return self.root_frame.height()


class ProcessTrace:
    """Represents trace of entire process, consists of a several thread traces."""
    def __init__(self, attributes, process_sections):
        """Attributes are name, path, etc.  Sections are thread traces or binary images."""
        self.attributes = attributes
        self.threads = []
        for process_section in process_sections:
            if process_section[0].lstrip().startswith("Thread"):
                self.threads.append(ThreadTrace(process_section))
            # Throw away everything else, e.g. binary images.


class TraceReport:
    def __init__(self, lines):
        # Parse general report header (4 sections)
        self.report_attributes = []
        for _ in range(4):
            section, lines = take_until_empty_line(lines)
            section_attributes = split_on_colon(section)
            self.report_attributes.append(section_attributes)
        # Parse process.
        process_section, lines = take_until_empty_line(lines)
        process_attributes = split_on_colon(process_section)
        process_sections = []
        while (lines is not None) and lines[0].startswith(" "):
            process_section, lines = take_until_empty_line(lines)
            process_sections.append(process_section)
        self.process_trace = ProcessTrace(process_attributes, process_sections)


# Parsing traces.
def take_until_empty_line(lines):
    """Returns first_lines and rest_lines."""
    assert len(lines) > 0
    assert len(lines[0]) > 0, "Empty line should be consumed earlier"
    empty_line_index = 1
    while empty_line_index < len(lines):
        if len(lines[empty_line_index]) == 0:
            break
        empty_line_index += 1
    nonempty_line_index = empty_line_index + 1
    while nonempty_line_index < len(lines):
        if len(lines[nonempty_line_index]) > 0:
            break
        nonempty_line_index += 1
    first_lines = lines[:empty_line_index]
    rest_lines = lines[nonempty_line_index:] if (nonempty_line_index < len(lines)) else None
    return first_lines, rest_lines


def split_on_colon(lines):
    """Returns pairs of (header, value)."""
    result = []
    for line in lines:
        split_result = line.split(":", 1)
        assert len(split_result) == 2, "Incorrect header: without a colon"
        header, value = split_result
        value = value.strip()
        result.append((header, value))
    return result


class SVG:
    _HEADER = """<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
version="1.1" xmlns="http://www.w3.org/2000/svg">"""
    _FOOTER = """</svg>"""
    _SYMBOL_WIDTH = 5.7
    _ELLIPSIS_WIDTH = 12.0

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.content_lines = []

    def add_rect(self, x, y, width, height, color):
        self.content_lines.append(
            '<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
            'height="{height:.1f}" fill="{color}" rx="2" ry="2" />'.format(
                x=x, y=y, width=width, height=height, color=color))

    def add_text(self, text, x, y):
        text = saxutils.escape(text)
        self.content_lines.append(
            '<text x="{x:.1f}" y="{y:.1f}" font-size="12" '
            'font-family="Helvetica">{text}</text>'.format(
                x=x, y=y, text=text))

    def add_bounded_text(self, text, x, y, width):
        text_width = len(text) * SVG._SYMBOL_WIDTH
        if text_width > width:
            bounded_text_length = int((width - SVG._ELLIPSIS_WIDTH) / SVG._SYMBOL_WIDTH)
            if bounded_text_length < 1:
                # width is too small to display at least 1 symbol with ellipsis.
                # Don't add any text.
                return
            else:
                text = text[:bounded_text_length]
                text += '\u2026'  # Add ellipsis
        self.add_text(text, x, y)

    def dump(self, stream):
        """stream should support writing unicode strings."""
        stream.write(self._HEADER.format(width=self.width, height=self.height))
        stream.write("\n")
        stream.write("\n".join(self.content_lines))
        stream.write("\n")
        stream.write(self._FOOTER)


class Color:
    @staticmethod
    def rgb(*components):
        return RGBColor(*components)

    @staticmethod
    def lab(*components):
        return LabColor(*components)

    @staticmethod
    def xyz(*components):
        return XYZColor(*components)

    def _native_components(self):
        assert False, "Should implement in subclasses"

    def as_rgb(self):
        assert False, "Should implement in subclasses"

    def as_lab(self):
        assert False, "Should implement in subclasses"

    def as_xyz(self):
        assert False, "Should implement in subclasses"

    def rgb_string(self):
        rgb_components = self.as_rgb()._native_components()
        return "rgb({0}, {1}, {2})".format(*rgb_components)

    def lab_components(self):
        return self.as_lab()._native_components()

    def _multiply_matrix_vector(self, matrix, vector):
        assert len(matrix[0]) == len(vector)
        result = [reduce(operator.add, map(operator.mul, row, vector))
                  for row in matrix]
        return result


class RGBColor(Color):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def _native_components(self):
        return self.r, self.g, self.b

    def as_rgb(self):
        return self

    def as_lab(self):
        return self.as_xyz().as_lab()

    def as_xyz(self):
        # See http://en.wikipedia.org/wiki/SRGB
        components = self._native_components()
        components = [c / 255.0 for c in components]
        # WARNING: gamma correction isn't performed, assume that RGB means not sRGB, but linear RGB
        rgb_to_xyz_coefficients = ((0.4124, 0.3576, 0.1805),
                                   (0.2126, 0.7152, 0.0722),
                                   (0.0193, 0.1192, 0.9505))
        xyz_components = self._multiply_matrix_vector(rgb_to_xyz_coefficients, components)
        return Color.xyz(*xyz_components)


class LabColor(Color):
    def __init__(self, l, a, b):
        self.l = l
        self.a = a
        self.b = b

    def _native_components(self):
        return self.l, self.a, self.b

    def as_rgb(self):
        return self.as_xyz().as_rgb()

    def as_lab(self):
        return self

    def as_xyz(self):
        # See http://en.wikipedia.org/wiki/Lab_color_space
        l, a, b = self._native_components()
        y = (l + 16.0) / 116.0
        x = y + a / 500.0
        z = y - b / 200.0
        def f_inverse(t):
            if t > (6.0 / 29.0):
                return t ** 3
            else:
                return 3 * ((6.0 / 29.0) ** 2) * (t - (4.0 / 29.0))
        xyz_components = map(lambda c, ref_c: ref_c * f_inverse(c), (x, y, z), XYZColor._WHITE_POINT_REF)
        return Color.xyz(*xyz_components)


class XYZColor(Color):
    _WHITE_POINT_REF = (0.95043, 1.00000, 1.08890)

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def _native_components(self):
        return self.x, self.y, self.z

    def as_rgb(self):
        # See http://en.wikipedia.org/wiki/SRGB
        components = self._native_components()
        xyz_to_rgb_coefficients = ((3.2406, -1.5372, -0.4986),
                                   (-0.9689, 1.8758, 0.0415),
                                   (0.0557, -0.2040, 1.0570))
        rgb_components = self._multiply_matrix_vector(xyz_to_rgb_coefficients, components)
        # WARNING: again, no gamma correction
        rgb_components = [int(c * 255) for c in rgb_components]
        return Color.rgb(*rgb_components)

    def as_lab(self):
        # See http://en.wikipedia.org/wiki/Lab_color_space
        components = self._native_components()
        components = map(lambda c, ref_c: c / ref_c, components, XYZColor._WHITE_POINT_REF)
        def f(t):
            if t > ((6.0 / 29.0) ** 3):
                return t ** (1.0 / 3.0)
            else:
                return (1.0 / 3.0) * ((29.0 / 6.0) ** 2) * t + (4.0 / 29.0)
        components = [f(c) for c in components]
        x, y, z = components
        l = 116.0 * y - 16.0
        a = 500.0 * (x - y)
        b = 200.0 * (y - z)
        return Color.lab(l, a, b)

    def as_xyz(self):
        return self


def linear_interpolation(from_list, to_list, t):
    assert 0.0 <= t <= 1.0
    assert len(from_list) == len(to_list)
    t = float(t)
    result = map(lambda from_el, to_el: (from_el + t * (to_el - from_el)),
                 from_list, to_list)
    return result


class ColorInterpolator:
    def __init__(self, from_color, to_color):
        self.from_color = from_color.as_lab()
        self.to_color = to_color.as_lab()

    def color_at_pos(self, position):
        from_components = self.from_color.lab_components()
        to_components = self.to_color.lab_components()
        result_components = linear_interpolation(from_components, to_components, position)
        return Color.lab(*result_components)


class ColorRectInterpolator:
    def __init__(self, left_bottom_color, left_top_color, right_bottom_color, right_top_color):
        self.left_bottom_color = left_bottom_color
        self.left_top_color = left_top_color
        self.right_bottom_color = right_bottom_color
        self.right_top_color = right_top_color

    def color_at_pos(self, x_pos, y_pos):
        left_components = linear_interpolation(
            self.left_bottom_color.lab_components(),
            self.left_top_color.lab_components(), y_pos)
        right_components = linear_interpolation(
            self.right_bottom_color.lab_components(),
            self.right_top_color.lab_components(), y_pos)
        result_components = linear_interpolation(
            left_components, right_components, x_pos)
        return Color.lab(*result_components)


class ColorGenerator:
    def __init__(self, base_color_triplet, max_deviation_triplet):
        self.base_color = base_color_triplet
        self.max_deviation = max_deviation_triplet

    def get_color_as_number(self):
        r, g, b = self.base_color
        dr, dg, db = self.max_deviation
        return (random.randint(r - dr, r + dr),
                random.randint(g - dg, g + dg),
                random.randint(b - db, b + db))

    def get_color_as_string(self):
        r, g, b = self.get_color_as_number()
        return "rgb({0}, {1}, {2})".format(r, g, b)


class UnicodeToBinaryStreamWrapper:
    def __init__(self, stream):
        self.stream = stream

    def write(self, unicode_str):
        self.stream.write(unicode_str.encode('utf-8'))

def main():
    # Read and parse spindump.
    filename = sys.argv[1]
    #filename = "test_data/Xcode_2013-08-30-203227_Volodymyrs-Mac-mini.hang"
    lines = []
    with open(filename, "rt") as f:
        lines = f.read().splitlines()
    report = TraceReport(lines)
    # Build SVG file.
    thread_trace = report.process_trace.threads[0]
    sample_height = 16.
    total_width = 1200
    max_stack_depth = thread_trace.max_stack_depth()
    height = sample_height * max_stack_depth
    svg = SVG(total_width, height)
    #color_generator = ColorGenerator((180, 115, 28), (25, 115, 28))
    # color_interpolator = ColorInterpolator(Color.rgb(0xff, 0xed, 0xa0),
    #                                        Color.rgb(0xf0, 0x3b, 0x20))
    color_interpolator = ColorRectInterpolator(
        Color.rgb(0xff, 0xed, 0xa0), Color.rgb(0xf0, 0x3b, 0x20),
        Color.rgb(0xf7, 0xfc, 0xb9), Color.rgb(0x31, 0xa3, 0x54))
    width_per_sample = total_width / thread_trace.root_frame.sample_count
    # Draw samples' rectangles.
    for frame, start, depth in thread_trace.root_frame.iteritems():
        x = start * width_per_sample
        y = height - depth * sample_height
        width = frame.sample_count * width_per_sample
        x_relative = float(x) / total_width
        y_relative = float(depth) / max_stack_depth
        color = color_interpolator.color_at_pos(x_relative, y_relative).rgb_string()
        svg.add_rect(x, y - sample_height, width, sample_height - 1., color)
        svg.add_bounded_text(frame.frame, x + 2., y - 4., width - 2.)
    svg.dump(UnicodeToBinaryStreamWrapper(sys.stdout))

if __name__ == '__main__':
    main()
