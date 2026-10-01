# Notification Service

**Status**: skeleton only — `router.py`/`service.py`/`repository.py` are
documented placeholders; no `models.py` (this service has no table of its
own). Built in `docs/DEVELOPMENT_PLAN.md` Phase 8, Days 41-42.

## Responsibility

Microsoft 365/Outlook email sends on the user's behalf: profile-update
reminders and review-queue alerts. OAuth 2.0 with least-privilege Graph API
scopes (`Mail.Send` only, per CLAUDE.md §6) — not full mailbox access.

## Inputs

None yet. Will take a recipient + template trigger from `scheduler` or
`review_workflow`.

## Outputs

None yet. Will send email via Graph API; no persisted state of its own.

## Events

Consumes triggers from `scheduler` (reminders) and `review_workflow`
(review-queue alerts). Not implemented yet.
