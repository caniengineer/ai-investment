"""Test configuration — mock external modules that may not be installed in CI."""

import sys
from unittest.mock import MagicMock

# Mock modules that require system libraries not available in all environments
for mod_name in ("yfinance", "psycopg2", "psycopg2.extensions", "psycopg2._psycopg"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
