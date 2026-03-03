import json
import os
import time

import psycopg
import requests

DATABASE_URL = os.getenv("DATABASE_URL")
ANALYZE_URL = os.getenv("ANALYZE_URL", "https://proscout-api.onrender.com/analyze")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))

if not DATABASE_URL:
    print("DATABASE_URL is not set. Exiting.")
    raise SystemExit(1)


def connect():
    print("Worker started. Connecting to database...")
    conn = psycopg.connect(DATABASE_URL)
    print("Connected to Supabase database.")
    return conn


conn = connect()

while True:
    print("Polling for analyses with status = done")
    analysis_id = None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, touches, completed_passes, failed_passes, positive_actions, negative_actions
                    FROM analyses
                    WHERE status = 'done' AND analysis_result IS NULL
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
                row = cur.fetchone()
                if not row:
                    time.sleep(POLL_SECONDS)
                    continue

                (
                    analysis_id,
                    touches,
                    completed_passes,
                    failed_passes,
                    positive_actions,
                    negative_actions,
                ) = row

                cur.execute(
                    "UPDATE analyses SET status = 'analyzing' WHERE id = %s",
                    (analysis_id,),
                )
                conn.commit()

                payload = {
                    "touches": touches,
                    "completed_passes": completed_passes,
                    "failed_passes": failed_passes,
                    "positive_actions": positive_actions,
                    "negative_actions": negative_actions,
                }

                response = requests.post(ANALYZE_URL, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()

                cur.execute(
                    "UPDATE analyses SET status = 'completed', analysis_result = %s WHERE id = %s",
                    (json.dumps(result), analysis_id),
                )
                conn.commit()
    except psycopg.OperationalError:
        print("Connection lost. Reconnecting...")
        conn = connect()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Worker error: {e}")
        if analysis_id is not None:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE analyses SET status = 'error' WHERE id = %s",
                        (analysis_id,),
                    )
                conn.commit()
            except Exception:
                pass
        time.sleep(POLL_SECONDS)
