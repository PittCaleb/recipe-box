"""Splits a recipe's instructions into steps, for cook mode on the recipe
page and for the JSON API."""

from html.parser import HTMLParser


class _StepParser(HTMLParser):
    """Each list item is a step, and so is each paragraph outside a list
    item. <br> line breaks inside one stay as newlines; other whitespace,
    including newlines in the HTML source, collapses to single spaces."""

    def __init__(self):
        super().__init__()
        self.steps = []
        self.current = []
        self.li_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self._finish()
            self.li_depth += 1
        elif tag == "br":
            self.current.append("\n")

    def handle_endtag(self, tag):
        if tag == "li":
            self.li_depth = max(0, self.li_depth - 1)
            self._finish()
        elif tag == "p":
            if self.li_depth:
                self.current.append(" ")
            else:
                self._finish()

    def handle_data(self, data):
        self.current.append(data.replace("\n", " "))

    def _finish(self):
        lines = (" ".join(line.split()) for line in "".join(self.current).split("\n"))
        text = "\n".join(line for line in lines if line)
        if text:
            self.steps.append(text)
        self.current = []


def instruction_steps(html):
    parser = _StepParser()
    parser.feed(html or "")
    parser.close()
    parser._finish()
    return parser.steps
