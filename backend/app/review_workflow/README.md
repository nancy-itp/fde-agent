# Review Workflow

**Status**: skeleton only (`models.py` is real; `router.py`/`service.py`/
`repository.py` are documented placeholders). Built in
`docs/DEVELOPMENT_PLAN.md` Phase 5, Days 21-25.

## Responsibility

Manager-facing review queue: exception routing on any confidence/mismatch
ambiguity (default-deny to manager review, never auto-accept, per
CLAUDE.md §4), approve/edit/override endpoints, and weighted overall-%
computation on approval. Owns `MismatchFlag` (`models.py`) — the
current-state record of a detected self-report-vs-tracker mismatch; the
append-only audit log of every approval/override/resolution CLAUDE.md §7
requires is a separate, not-yet-designed table.

## Inputs

None yet. Will take `PerformanceScore` drafts from `scoring` and detected
mismatches to resolve.

## Outputs

None yet. Will finalize `PerformanceScore` rows, resolve `MismatchFlag`
rows, and write to the audit log.

## Events

Consumes `scoring`'s drafts; produces the audit trail `notification` and
any dashboard read from. Not implemented yet.
