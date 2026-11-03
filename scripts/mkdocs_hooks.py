"""mkdocs hook: show the runnable blocks of the pages as plain code blocks.

A page marks a command block as ``bash run ...`` (with options) and the output that follows it as ``text output``, so that a test
can execute the commands and check the output (see scripts/run_doc_snippets.py). The markdown renderer knows a block by its language
word alone, so this hook cuts the info strings down to ``bash`` and ``text`` before the page is rendered. GitHub does the same on
its own when it shows the README.
"""
import re

_RUN = re.compile(r"^```bash run[^\n]*$", re.M)
_OUT = re.compile(r"^```text output[^\n]*$", re.M)


def on_page_markdown(markdown, **kwargs):
    return _OUT.sub("```text", _RUN.sub("```bash", markdown))
