"""Test-wide setup.

`app.core.config.Settings` is constructed at import time and
`jwt_secret_key` has no default, so a CI checkout with no `.env` file would
otherwise fail every test at collection. Set it (and nothing else — every
other setting already has a usable default) before any test module gets a
chance to import `app.main`.

Also force PRIO_MCP_BASE_URL/TOKEN empty here, overriding whatever a
developer's local `backend/.env` has configured (env vars take precedence
over the `.env` file in pydantic-settings' resolution order, so this
shadows it rather than being shadowed by it). Without this, a test meant
to exercise "the connector is unconfigured" would instead pick up a real
developer's real staging credentials and make a real network call — tests
must never depend on, or accidentally exercise, real secrets.
"""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")
os.environ["PRIO_MCP_BASE_URL"] = ""
os.environ["PRIO_MCP_TOKEN"] = ""
