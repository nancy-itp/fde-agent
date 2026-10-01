"""External-adapter layer for the Notification Service.

Not yet implemented — see `service.py`'s docstring for scope and phase.
This service has no table of its own (no `models.py`): its job is calling
Microsoft Graph, not persisting state. Expect this to end up structured
like `prio_integration` (a `client.py` for the Graph HTTP/OAuth layer, this
file as typed wrappers over it) rather than a traditional SQLAlchemy
repository.
"""

from __future__ import annotations
