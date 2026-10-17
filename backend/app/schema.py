"""Eye Spy database schema (Tiger Data / PostgreSQL + TimescaleDB).

Applied by `python -m scripts.init_db`. Every statement is idempotent, so it is
safe to re-run. Statements are kept as a list because they run one at a time in
autocommit mode: TimescaleDB refuses some of them (continuous aggregates)
inside a transaction block.
"""

STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS timescaledb",

        # Eye analysis history
    

    # People. auth0_sub links a row to an Auth0 user (the token's "sub" claim).
    """
    CREATE TABLE IF NOT EXISTS providers (
        id          SERIAL PRIMARY KEY,
        auth0_sub   TEXT UNIQUE NOT NULL,
        name        TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS patients (
        id            SERIAL PRIMARY KEY,
        auth0_sub     TEXT UNIQUE NOT NULL,
        first_name    TEXT NOT NULL,
        last_name     TEXT NOT NULL,
        provider_id   INT REFERENCES providers(id),
        timezone      TEXT NOT NULL DEFAULT 'America/New_York',
        humor_level   TEXT NOT NULL DEFAULT 'full' CHECK (humor_level IN ('full', 'mild', 'off')),
        surgery_date  DATE
    )
    """,
    """
        CREATE TABLE IF NOT EXISTS eye_analyses (
            id BIGSERIAL PRIMARY KEY,
            patient_id INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            analysis TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
            # Add image storage to existing eye analyses
        """
        ALTER TABLE eye_analyses
        ADD COLUMN IF NOT EXISTS image_data BYTEA
        """,
        """
        ALTER TABLE eye_analyses
        ADD COLUMN IF NOT EXISTS image_type TEXT
        """,
        """
        ALTER TABLE eye_analyses
        ALTER COLUMN analysis DROP NOT NULL
        """,

    # Prescriptions. A schedule is "this drop, this eye, this many drops".
    # Schedule steps hold the times per day for a date range, which is how a
    # steroid taper is expressed (4x/day week 1, 3x/day week 2, and so on).
    """
    CREATE TABLE IF NOT EXISTS medications (
        id       SERIAL PRIMARY KEY,
        name     TEXT UNIQUE NOT NULL,
        purpose  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schedules (
        id             SERIAL PRIMARY KEY,
        patient_id     INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        medication_id  INT NOT NULL REFERENCES medications(id),
        eye            TEXT NOT NULL CHECK (eye IN ('left', 'right', 'both')),
        drops          INT NOT NULL DEFAULT 1 CHECK (drops > 0)
    )
    """,
    # dose_times are local wall-clock times in the patient's timezone; end_date is inclusive.
    """
    CREATE TABLE IF NOT EXISTS schedule_steps (
        id           SERIAL PRIMARY KEY,
        schedule_id  INT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
        start_date   DATE NOT NULL,
        end_date     DATE NOT NULL,
        dose_times   TIME[] NOT NULL,
        CHECK (end_date >= start_date)
    )
    """,

    # Docks. Only a SHA-256 of the device token is stored.
    """
    CREATE TABLE IF NOT EXISTS devices (
        id            SERIAL PRIMARY KEY,
        patient_id    INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        token_sha256  TEXT UNIQUE NOT NULL,
        last_seen_at  TIMESTAMPTZ
    )
    """,

    # dose_events: one row per scheduled dose, plus lift/return times and the
    # result flag. A lift that matches no scheduled dose gets its own row with
    # schedule_id NULL, scheduled_at = lifted_at and flag 'too_frequent'.
    # 'pending' means not resolved yet. The primary key includes scheduled_at
    # because hypertable keys must include the time column.
    """
    CREATE TABLE IF NOT EXISTS dose_events (
        id            BIGSERIAL,
        patient_id    INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        schedule_id   INT REFERENCES schedules(id) ON DELETE CASCADE,
        scheduled_at  TIMESTAMPTZ NOT NULL,
        lifted_at     TIMESTAMPTZ,
        returned_at   TIMESTAMPTZ,
        flag          TEXT NOT NULL DEFAULT 'pending'
                      CHECK (flag IN ('pending', 'on_time', 'late', 'early', 'missed', 'too_frequent')),
        PRIMARY KEY (id, scheduled_at)
    )
    """,
    "SELECT create_hypertable('dose_events', by_range('scheduled_at', INTERVAL '7 days'), if_not_exists => TRUE)",
    # One row per schedule per slot, so materializing doses twice is harmless.
    "CREATE UNIQUE INDEX IF NOT EXISTS dose_events_schedule_slot ON dose_events (schedule_id, scheduled_at)",
    "CREATE INDEX IF NOT EXISTS dose_events_patient_time ON dose_events (patient_id, scheduled_at DESC)",

    # Raw lift/return signals from the dock, kept for debugging and audit.
    """
    CREATE TABLE IF NOT EXISTS device_events (
        device_id    INT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
        patient_id   INT NOT NULL,
        event        TEXT NOT NULL CHECK (event IN ('lifted', 'returned')),
        at           TIMESTAMPTZ NOT NULL,
        received_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "SELECT create_hypertable('device_events', by_range('at', INTERVAL '7 days'), if_not_exists => TRUE)",

    # Continuous aggregate behind the provider dashboard: doses per patient per
    # day, by result. Days are bucketed in America/New_York (one demo timezone;
    # a continuous aggregate cannot vary the timezone per row).
    # materialized_only = false so today's numbers include rows not yet materialized.
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS daily_adherence
    WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
    SELECT
        patient_id,
        time_bucket(INTERVAL '1 day', scheduled_at, 'America/New_York') AS day,
        count(*) FILTER (WHERE flag <> 'too_frequent') AS scheduled,
        count(*) FILTER (WHERE flag = 'on_time')       AS on_time,
        count(*) FILTER (WHERE flag = 'late')          AS late,
        count(*) FILTER (WHERE flag = 'early')         AS early,
        count(*) FILTER (WHERE flag = 'missed')        AS missed,
        count(*) FILTER (WHERE flag = 'too_frequent')  AS too_frequent,
        count(*) FILTER (WHERE flag = 'pending')       AS pending
    FROM dose_events
    GROUP BY patient_id, day
    WITH NO DATA
    """,
    """
    SELECT add_continuous_aggregate_policy('daily_adherence',
        start_offset      => INTERVAL '30 days',
        end_offset        => INTERVAL '1 hour',
        schedule_interval => INTERVAL '30 minutes',
        if_not_exists     => TRUE)
    """,
]
