import importlib.metadata

import libpython_linkcheck


def test_version_matches_metadata():
    assert libpython_linkcheck.__version__ == importlib.metadata.version("libpython-linkcheck")
