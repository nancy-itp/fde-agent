-- ============================================================================
-- PRIO database schema — reverse-engineered from prio_data_20260928.xlsx
-- ============================================================================
-- Source: one-time export of the `task_management` database, snapshot taken
-- 2026-09-28 20:41:26 +05:30. Types, nullability and enum value lists below
-- were inferred from the actual exported rows (20 users, 238 tasks, 936
-- work_candidates, 1528 audit_logs, etc.) — not from PRIO's real source code,
-- so verify against PRIO's actual migrations before running this anywhere
-- that matters. Written in ANSI-ish SQL (works on Postgres with minor tweaks
-- for other engines) since PRIO's actual DB engine wasn't confirmed.
--
-- Six tables exist in PRIO but had 0 rows in this export, so their real
-- column structure is UNKNOWN and is NOT guessed here:
--   workstreams, task_blockers, task_evidence, task_reviews,
--   task_lists, task_list_items
-- Get their real DDL from Dhruvin before building anything that depends on
-- them (tasks.workstream_id currently points at one of them but is unused).
-- ============================================================================

CREATE TABLE users (
    id                      INTEGER PRIMARY KEY,
    name                    VARCHAR(255) NOT NULL,
    email                   VARCHAR(255) NOT NULL UNIQUE,
    account_status          VARCHAR(50) NOT NULL,   -- observed: ACTIVE only (others likely exist, e.g. PENDING, DISABLED — audit_logs has USER_DISABLED)
    manager_id              INTEGER REFERENCES users(id),
    manager_delegated       BOOLEAN NOT NULL DEFAULT FALSE,
    delegated_by_user_id    INTEGER REFERENCES users(id),
    created_at              TIMESTAMP NOT NULL,
    updated_at              TIMESTAMP NOT NULL
    -- Note: password_hash column exists in the real table but was stripped
    -- from this export. Deleted accounts (ids 1, 14 in this snapshot) are
    -- hard-deleted from `users` but still referenced from other tables —
    -- don't assume every foreign id here resolves to a live row.
);

CREATE TABLE user_roles (
    user_id     INTEGER NOT NULL REFERENCES users(id),
    role        VARCHAR(50) NOT NULL,   -- observed: EMPLOYEE, MANAGER, SYSTEM_ADMIN
    PRIMARY KEY (user_id, role)         -- a user can hold more than one role
);

CREATE TABLE teams (
    id              INTEGER PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    manager_id      INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP NOT NULL,
    kind            VARCHAR(50)         -- always NULL in this export; purpose unconfirmed
);

CREATE TABLE team_members (
    id              INTEGER PRIMARY KEY,
    team_id         INTEGER NOT NULL REFERENCES teams(id),
    employee_id     INTEGER NOT NULL REFERENCES users(id),
    added_at        TIMESTAMP NOT NULL
);

CREATE TABLE work_sources (
    id              INTEGER PRIMARY KEY,
    source_type     VARCHAR(50) NOT NULL,   -- observed: MANUAL only; PRIO likely also ingests other channels (Slack/meeting bots etc.)
    external_id     VARCHAR(255),
    content_hash    VARCHAR(128) NOT NULL,  -- intended to dedupe identical submissions; confirm uniqueness is now enforced (was not, per Dhruvin, now fixed)
    title           VARCHAR(255),
    occurred_at     TIMESTAMP,
    metadata        JSON,                   -- free-form: raw transcript/text + submitted_by, etc.
    created_at      TIMESTAMP NOT NULL
);

CREATE TABLE tasks (
    id                  INTEGER PRIMARY KEY,
    parent_task_id      INTEGER REFERENCES tasks(id),   -- subtasks; 27/238 rows in this export had one
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    created_by          INTEGER NOT NULL REFERENCES users(id),
    team_id             INTEGER REFERENCES teams(id),   -- NULL on 41% of tasks in this export — future-scope field, don't assume populated
    priority_category   VARCHAR(20) NOT NULL,           -- observed: HIGH, MEDIUM, LOW
    priority_index      INTEGER NOT NULL,                -- rank within category; not a scoring input, informational
    status              VARCHAR(30) NOT NULL,            -- observed: NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED, NEEDS_MANAGER_REVIEW
    start_date          DATE,
    due_date            DATE,                            -- NOT required on every task by design — 45% NULL in this export
    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL,
    reviewed_by         INTEGER REFERENCES users(id),    -- populated only when a manager review actually happened
    owner_id            INTEGER REFERENCES users(id),    -- always NULL in this export — real assignment lives in task_assignments; NULL here just means "no assignee yet" for a given task, not a bug
    workstream_id       INTEGER,                          -- FK to the empty `workstreams` table; unused, ignore per Dhruvin
    task_type           VARCHAR(50),                      -- always NULL in this export; unused
    eta_date            DATE,                             -- always NULL in this export; unused
    completed_at        TIMESTAMP,                        -- always NULL, even on COMPLETED tasks — NOT the source of truth for completion time; use audit_logs.STATUS_CHANGED instead (see aggregation plan)
    source_id           INTEGER REFERENCES work_sources(id) -- always NULL in this export; would link a task back to the evidence that created it
);

CREATE TABLE task_assignments (
    id              INTEGER PRIMARY KEY,
    task_id         INTEGER NOT NULL REFERENCES tasks(id),
    employee_id     INTEGER NOT NULL REFERENCES users(id),
    assigned_at     TIMESTAMP NOT NULL,
    assigned_by     INTEGER NOT NULL REFERENCES users(id)
    -- This is the real ownership table — a task can have >1 row here (multiple assignees).
    -- Always join through this table for "who is this task's evidence for", never tasks.owner_id.
);

CREATE TABLE task_updates (
    id              INTEGER PRIMARY KEY,
    task_id         INTEGER NOT NULL REFERENCES tasks(id),
    employee_id     INTEGER NOT NULL REFERENCES users(id),
    update_date     DATE NOT NULL,
    status          VARCHAR(30) NOT NULL,   -- mirrors tasks.status vocabulary
    note            TEXT,
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP NOT NULL
    -- Future scope per Dhruvin — only 2 rows existed in this export. This is
    -- the intended source for "comment/status-update activity" once it's
    -- actually used; don't build a metric on it yet.
);

CREATE TABLE work_candidates (
    id                  INTEGER PRIMARY KEY,
    candidate_id        VARCHAR(64) NOT NULL UNIQUE,   -- e.g. 'wc_e4a55c145c...'
    source_id           INTEGER NOT NULL REFERENCES work_sources(id),
    segment_ref         VARCHAR(20),                    -- e.g. 'L1', points at a segment within the source
    action              VARCHAR(20) NOT NULL,           -- observed: CREATE, IGNORE, REVIEW, UPDATE, DUPLICATE
    intent              VARCHAR(20) NOT NULL,           -- observed: NEW_WORK, BLOCKER, NONE
    status              VARCHAR(20) NOT NULL,           -- observed: PENDING, APPROVED, REJECTED
    proposal            JSON,                            -- the extraction agent's full draft (evidence, confidence, reasoning)
    edited_values       JSON,
    final_values        JSON,
    result              JSON,                            -- what actually happened on apply, e.g. {"task_id":..., "mutation":"TASK_CREATED"}
    target_task_id      INTEGER REFERENCES tasks(id),
    submitted_by        INTEGER NOT NULL REFERENCES users(id),
    reviewed_by         INTEGER REFERENCES users(id),
    reviewed_at         TIMESTAMP,
    reject_reason       TEXT,
    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL
    -- This is PRIO's own agent-drafts / human-reviews-exceptions layer,
    -- structurally similar to the FDE scoring agent's own workflow — not
    -- itself a scoring data source, but useful precedent to reuse patterns from.
);

CREATE TABLE notifications (
    id                  INTEGER PRIMARY KEY,
    recipient_id        INTEGER NOT NULL REFERENCES users(id),
    type                VARCHAR(50) NOT NULL,   -- observed: USER_SIGNUP_PENDING, USER_APPROVED, TASK_ASSIGNED, SUBTASK_ASSIGNED
    title               VARCHAR(255) NOT NULL,
    message             TEXT NOT NULL,
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP NOT NULL,
    related_user_id     INTEGER REFERENCES users(id)
    -- Original table also has a secret_payload column, stripped from this
    -- export; password-reset notification rows were removed entirely.
);

CREATE TABLE performance_points (
    id                      INTEGER PRIMARY KEY,
    awarded_to_user_id      INTEGER NOT NULL REFERENCES users(id),
    awarded_by_user_id      INTEGER NOT NULL REFERENCES users(id),
    points                  INTEGER NOT NULL,   -- can be negative (observed -10 and +10 in this export)
    reason                  TEXT,                -- always NULL in this export
    created_at              TIMESTAMP NOT NULL,
    updated_at              TIMESTAMP NOT NULL
    -- Manual manager-awarded adjustment, separate from the task-tracker-derived
    -- signals below. Only 4 rows existed in this export — confirm with Dhruvin
    -- whether this is meant to feed FDE scoring at all before using it.
);

CREATE TABLE audit_logs (
    id              INTEGER PRIMARY KEY,
    actor_id        INTEGER REFERENCES users(id),
    action          VARCHAR(50) NOT NULL,   -- observed 17 distinct values, incl. STATUS_CHANGED, TASK_CREATED, TASK_EDITED, PRIORITY_CHANGED, EMPLOYEE_ASSIGNED, WORK_CANDIDATE_*, TEAM_*
    entity_type     VARCHAR(30) NOT NULL,   -- observed: Task, TASK, Team, WorkCandidate — NOTE inconsistent casing for Task/TASK in this export, normalize (UPPER()) before matching on it
    entity_id       INTEGER,
    old_value       TEXT,
    new_value       TEXT,
    created_at      TIMESTAMP NOT NULL,
    actor_type      VARCHAR(20),            -- observed: USER only, but nullable
    metadata        JSON
    -- This is the source of truth for reopen/rework detection: filter
    -- action = 'STATUS_CHANGED' and read old_value/new_value as the status
    -- transition. Also retains history for deleted tasks/teams, so entity_id
    -- won't always resolve to a live row in tasks/teams.
);
