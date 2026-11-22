"""Anki add-on: insert pronunciation audio for a field with one click.

The heavy lifting lives in pure-Python modules (voices, text, net, audio,
providers, core) that are testable without Anki. GUI wiring only happens
when running inside Anki.
"""

try:
    from aqt import mw
except ImportError:  # running outside Anki (tests, tooling)
    mw = None

if mw is not None:
    from .editor_integration import setup

    setup()
