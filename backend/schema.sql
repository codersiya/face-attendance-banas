-- Reference schema. In practice this is auto-created by SQLAlchemy on
-- app startup (see app/main.py), but kept here for documentation / manual
-- provisioning / DBA review.
--
-- No pgvector extension is used here. Embeddings are stored using plain
-- native PostgreSQL arrays (double precision[]) - works on any stock
-- PostgreSQL instance, no extension install required.
CREATE TABLE IF NOT EXISTS employees (
    emp_id              VARCHAR(30) PRIMARY KEY,        -- user-entered string ID, primary key
    emp_code            VARCHAR(30) UNIQUE NOT NULL,     -- user-entered code
    employee_name       VARCHAR(150) NOT NULL,
    department          VARCHAR(100) NOT NULL,
    designation         VARCHAR(100) NOT NULL,
    shift_start_time    TIME NOT NULL,
    shift_end_time      TIME NOT NULL,
    grace_time_minutes  INTEGER NOT NULL DEFAULT 0,
    late_entry_minutes  INTEGER NOT NULL DEFAULT 0,
    overtime_rules      TEXT,
    embedding_front     DOUBLE PRECISION[],
    embedding_left      DOUBLE PRECISION[],
    embedding_right     DOUBLE PRECISION[],
    is_enrolled         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Similarity search (face matching) is done in Python by comparing these
-- arrays with a Euclidean distance function (see app/face_service.py),
-- since there is no vector similarity operator without pgvector.