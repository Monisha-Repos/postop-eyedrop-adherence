"""Register this backend's DEVICE_TOKEN as a dock for a patient, without re-seeding.

Run from backend/:
    python -m scripts.register_device            # dock for the demo patient (DEMO_PATIENT_SUB, else Ann)
    python -m scripts.register_device --patient-id 3

Only adds a row: docks already registered (for example by a teammate's seed) keep working.
"""
import argparse

import psycopg
from psycopg.rows import dict_row

from app import config
from app.auth import hash_device_token


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patient-id", type=int, help="patients.id to attach the dock to")
    args = parser.parse_args()

    if not config.DEVICE_TOKEN:
        raise SystemExit("Set DEVICE_TOKEN in backend/.env first.")

    with psycopg.connect(config.DATABASE_URL, row_factory=dict_row) as conn:
        if args.patient_id:
            patient = conn.execute(
                "SELECT id, first_name FROM patients WHERE id = %s", (args.patient_id,)
            ).fetchone()
        else:
            # The demo patient may have been re-linked to a real Auth0 login, so fall back to Ann.
            patient = conn.execute(
                """
                SELECT id, first_name FROM patients
                WHERE auth0_sub = %s OR (first_name = 'Ann' AND last_name = 'Lee')
                ORDER BY (auth0_sub = %s) DESC LIMIT 1
                """,
                (config.DEMO_PATIENT_SUB, config.DEMO_PATIENT_SUB),
            ).fetchone()
        if not patient:
            raise SystemExit("Patient not found. Pass --patient-id.")

        row = conn.execute(
            """
            INSERT INTO devices (patient_id, token_sha256) VALUES (%s, %s)
            ON CONFLICT (token_sha256) DO NOTHING
            RETURNING id
            """,
            (patient["id"], hash_device_token(config.DEVICE_TOKEN)),
        ).fetchone()

        if row:
            print(f"Dock {row['id']} registered for {patient['first_name']} (patient {patient['id']}).")
        else:
            owner = conn.execute(
                "SELECT d.id, p.first_name FROM devices d JOIN patients p ON p.id = d.patient_id"
                " WHERE d.token_sha256 = %s",
                (hash_device_token(config.DEVICE_TOKEN),),
            ).fetchone()
            print(f"This token is already registered: dock {owner['id']} for {owner['first_name']}.")


if __name__ == "__main__":
    main()
