import nh3

ALLOWED_TAGS = {"p", "br", "strong", "em", "ul", "ol", "li"}


def sanitize_instructions(html):
    return nh3.clean(html or "", tags=ALLOWED_TAGS, attributes={})
