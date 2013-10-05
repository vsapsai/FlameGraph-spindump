#!/usr/bin/env python

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

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.content_lines = []

    def add_rect(self, x, y, width, height, color):
        self.content_lines.append('<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" fill="{color}" rx="2" ry="2" />'.format(
            x=x, y=y, width=width, height=height, color=color))

    def add_text(self, text, x, y):
        text = saxutils.escape(text)
        self.content_lines.append('<text x="{x:.1f}" y="{y:.1f}" font-size="12" font-family="Helvetica">{text}</text>'.format(
            x=x, y=y, text=text))

    def dump(self, stream):
        stream.write(self._HEADER.format(width=self.width, height=self.height))
        stream.write("\n")
        stream.write("\n".join(self.content_lines))
        stream.write("\n")
        stream.write(self._FOOTER)


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


def iterate_frames(frame):
    def _generator(frame, start, depth):
        yield (frame, start, depth)
        child_start = start
        for child_frame in frame.child_samples:
            for t in _generator(child_frame, child_start, depth + 1):
                yield t
            child_start += child_frame.sample_count
    return _generator(frame, 0, 0)


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
    width = 1200
    height = sample_height * thread_trace.max_stack_depth()
    svg = SVG(width, height)
    color_generator = ColorGenerator((180, 115, 28), (25, 115, 28))
    width_per_sample = width / thread_trace.root_frame.sample_count
    # Draw samples' rectangles.
    for frame, start, depth in iterate_frames(thread_trace.root_frame):
        x = start * width_per_sample
        y = height - depth * sample_height
        width = frame.sample_count * width_per_sample
        svg.add_rect(x, y - sample_height, width, sample_height - 1., color_generator.get_color_as_string())
        svg.add_text(frame.frame, x + 2., y - 4.)
    svg.dump(sys.stdout)

if __name__ == '__main__':
    main()
