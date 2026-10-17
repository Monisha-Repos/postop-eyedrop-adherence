# Eye Spy: build log

A record of what was built for the baseline, why each piece exists, and how to run it.
Baseline written 2026-10-17. Nothing has been committed or pushed.

---

## 1. What exists now

| Part | Folder | Language | Status |
| --- | --- | --- | --- |
| Backend API | `backend/` | Python (FastAPI) | Written; rules and reminder logic unit-tested (16 tests pass). Not yet run against a live database. |
| Database schema | `backend/app/schema.py` | Python (SQL kept in Python strings) | Written; not yet applied to Tiger Cloud. |
| Patient + provider app | `app/` | React (JavaScript/JSX), HTML, CSS | Written; `npm run build` succeeds. Not yet tested on an iPad. |
| Dock firmware | `firmware/` | MicroPython | Written; syntax-checked. Not yet flashed to hardware. |
| Reminder evals | `evals/` | Python | Runner works offline. Live Gemini numbers not yet produced. |
| Wiring notes | `hardware/README.md` | (docs) | Pin map and LED/sound behaviour. |

### Language rule

The project uses **Python, React (JS/JSX), HTML and CSS only**:

- The iPad app is a **React web app** that runs full-screen on the iPad via Safari's "Add to Home Screen". It replaces the SwiftUI app the README describes.
- The ESP32 runs **MicroPython** instead of Arduino C++.
- Postgres still needs SQL, but it lives only inside Python strings (`app/schema.py`, queries in `app/doses.py` and the routes). There are no `.sql` files.
- Config and docs are JSON (`package.json`, `evals/cases.json`), `.env` files and Markdown.

> `README.md` has been updated to match: React web app, Python backend, MicroPython firmware, setup steps and repository structure.

---

## 2. How the pieces talk

```
Dock (MicroPython) --X-Device-Token--> Backend (FastAPI) --> Tiger Data (Postgres + TimescaleDB)
React app (iPad)   --Auth0 JWT------> Backend           --> Gemini (reminder wrapper + TTS)
                                       Backend           --> Auth0 JWKS (token signature check)
```

- The **dock** polls `GET /device/status` every 15 s and posts `lifted` / `returned` events.
- The **app** signs in with Auth0, calls `GET /me` to learn the role, then shows the patient or provider screen.
- The **backend** holds every secret (database URL, Gemini key), so nothing sensitive ships in the browser bundle or on the device.

---

## 3. Repository layout

```
.gitignore              # added: .env, .env.local, firmware/config.py, .venv, app/dist
BUILD_LOG.md            # this file
backend/
  requirements.txt
  .env.example          # every backend setting, with comments
  app/
    main.py             # FastAPI app, CORS, /health, /me
    config.py           # env settings
    db.py               # psycopg connection pool
    schema.py           # all tables, hypertables, continuous aggregate
    auth.py             # Auth0 JWT check, roles, device token check
    rules.py            # pure dose rules (on_time / late / early / missed / too_frequent)
    doses.py            # DB side of the rules: materialize, sweep, match lifts
    reminders.py        # templates + Gemini wrapper + guardrail checks
    tts.py              # Gemini text-to-speech -> WAV
    routes/
      device.py         # /device/status, /device/events
      patient.py        # /patient/today, /patient/reminder, audio, settings
      provider.py       # /provider/patients, adherence, doses
  scripts/
    init_db.py          # applies schema.py
    seed.py             # demo provider, 2 patients, regimen, 1-2 weeks of history
  tests/
    test_rules.py
    test_reminders.py
app/
  package.json, vite.config.js, index.html, .env.example
  src/
    main.jsx, App.jsx   # entry, role-based routing
    config.js           # VITE_* settings
    auth.jsx            # Auth0 (or local dev bypass) behind one small interface
    api.js              # fetch wrapper + date helpers
    flags.js            # flag labels/symbols, dose text helpers
    reminderPlayer.js   # Gemini audio playback, browser speech fallback, Safari audio unlock
    styles.css          # dark / high-contrast theme, large type
    components/         # Login, SetupNeeded, Modal, FlagBadge
    patient/            # PatientHome, PatientSettings, TodayList
    provider/           # ProviderHome, PatientDetail, AdherenceChart
firmware/
  main.py               # dock logic
  config_example.py     # WiFi / backend URL / device token
hardware/
  README.md             # pin map, wiring, enclosure notes
evals/
  cases.json            # 12 reminder cases
  run_evals.py          # runs cases x 3 humor levels, writes evals/results.md
```

---

## 4. What each part does and why

### 4.1 Database (`backend/app/schema.py`)

| Object | Why it exists |
| --- | --- |
| `providers`, `patients` | People. `auth0_sub` links a row to an Auth0 login. `patients.provider_id` is what limits a provider to their own patients. `humor_level` stores the patient's reminder setting. |
| `medications` | Drop names (antibiotic, steroid, anti-inflammatory). |
| `schedules` | "This drop, this eye, this many drops" for a patient. |
| `schedule_steps` | Times per day over a date range. **This is how the steroid taper works**: one step per week (4x, 3x, 2x, 1x). |
| `devices` | Maps a dock to a patient. Stores only a **SHA-256 of the token**, so a database leak doesn't leak working device tokens. |
| `dose_events` (**hypertable**) | One row per scheduled dose with `scheduled_at`, `lifted_at`, `returned_at`, `flag`. Partitioned by time because it grows forever and almost every query is "recent rows for a patient". |
| `device_events` (**hypertable**) | Raw lift/return signals, kept for debugging ("did the dock even send it?") and as an audit trail. |
| `daily_adherence` (**continuous aggregate**) | Daily counts per patient per flag. Powers the provider chart without scanning raw rows. `materialized_only = false` keeps today's numbers live. Refreshed every 30 min. |

Two choices that differ slightly from the README:

- **A `pending` flag was added.** A dose row exists before it's taken, so it needs a "not resolved yet" state.
- **Daily buckets use one timezone** (`America/New_York`), because a continuous aggregate can't vary the timezone per patient. That's fine for a Florida demo.

Every statement is idempotent, so `init_db` can be re-run safely. The statements run one at a time in autocommit mode because TimescaleDB rejects continuous-aggregate creation inside a transaction.

### 4.2 Dose rules (`backend/app/rules.py`)

"Rules decide": every flag comes from this deterministic, unit-tested code, never from the AI model.

| Constant | Value | Meaning |
| --- | --- | --- |
| `ON_TIME_WINDOW` | ±30 min | Lift within this window of the scheduled time is `on_time` |
| `EARLY_LIMIT` | 2 h | A lift up to 2 h before a dose counts toward it (as `early`) |
| `MISSED_AFTER` | 3 h | After 3 h a pending dose becomes `missed`; until then it is "due" and the dock alarms |
| `MIN_GAP` | 5 min | Different drops scheduled at the same time are staggered (08:00, 08:05, 08:10), because drops need a few minutes between them |

**Matching a lift to a dose** (`choose_dose`):
1. The oldest dose that is already due and not yet missed. A late dose is more likely than a very early one.
2. Otherwise, the soonest upcoming dose within 2 h.
3. Otherwise there's no match: a `too_frequent` row is recorded with `schedule_id = NULL`.

Constants are at the top of the file. They are product decisions, not clinical guidance, and should be reviewed with a clinician.

### 4.3 Dose tracking in the database (`backend/app/doses.py`)

- **`ensure_doses`** turns schedule steps into pending `dose_events` rows for the last 7 days through tomorrow. Inserts use `ON CONFLICT DO NOTHING`, so they're idempotent, and an in-memory cache avoids repeating them on every 15 s poll. Past days are included on purpose: if the dock was offline all day, those doses still appear and become `missed`.
- **`sweep_missed`** marks overdue pending doses `missed`. It runs on each dock poll and each app/dashboard read, so no background scheduler is needed for a hackathon.
- **`record_lift` / `record_return`** apply dock events using the rules above.

### 4.4 Reminders (`backend/app/reminders.py`, `backend/app/tts.py`)

This follows the README's "what is true vs how it is said" split:

1. **Template (facts):** `instruction_for()` builds the sentence with medication, drops, eye and time from database values. Example: *"It's time for your Prednisolone: 1 drop in your left eye."*
2. **Gemini (personality):** writes only an `opener` and a `closer` as JSON. It is told the situation (due, late, missed, ...) and the humor level, but is **not given the instruction**, so it can't rewrite it.
3. **Guardrails:** `wrapper_problems()` rejects a wrapper if it contains a number, a medication name, medical wording (doctor, dose, drop, skip, stop, eye, ...), praise after a late, early, missed or too_frequent dose, scolding on an on-time dose, or too many words. A rejected wrapper is retried once, then replaced with built-in lines (`FALLBACK`).
4. **Humor off:** no model call at all. The script is "Hello Ann." plus the instruction.
5. **TTS:** `tts.synthesize()` sends the final script to Gemini TTS, wraps the raw 24 kHz PCM as WAV and caches it. If there's no key or the call fails, the app uses the browser's built-in voice.

The missed-dose template says "please call your eye doctor's office". That safety line comes from the template, never the model.

### 4.5 Auth (`backend/app/auth.py`)

- Validates Auth0 access tokens (RS256, JWKS, audience, issuer) with PyJWT.
- Roles come from a custom claim (`https://eyespy.app/roles`) added by an Auth0 Action (see section 6.2).
- A request is allowed only if the token has the role **and** a matching `patients`/`providers` row exists for its `sub`.
- Provider routes filter on `provider_id`. Another provider's patient returns **404, not 403**, so the API doesn't reveal that the patient exists.
- Docks authenticate with the `X-Device-Token` header (looked up by hash).
- **`DEV_AUTH_BYPASS`** (off by default) accepts `Bearer dev:<sub>` for local demos without Auth0. The server logs a warning on startup when it's on. Never enable it on a public host.

### 4.6 API

| Method | Path | Who | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | anyone | Liveness |
| GET | `/me` | signed in | Role, name, humor level; the app picks its screen from this |
| GET | `/device/status` | dock | `dose_due`, `dose_id`, `medication`, `server_time` |
| POST | `/device/events` | dock | `{"event": "lifted"|"returned", "age_ms": 0}` → flag result |
| GET | `/patient/today` | patient | Due dose, next dose, today's doses |
| GET | `/patient/reminder` | patient | Script for right now (due dose, else latest result, else next dose) |
| GET | `/patient/reminder/{id}/audio` | patient | WAV of that exact script (503 means use on-device voice) |
| PATCH | `/patient/settings` | patient | `{"humor_level": "full"|"mild"|"off"}` |
| GET | `/provider/patients` | provider | Own patients with 7-day taken %, on-time %, missed count |
| GET | `/provider/patients/{id}/adherence?days=14` | provider | Daily rows from the continuous aggregate |
| GET | `/provider/patients/{id}/doses?days=3` | provider | Recent dose rows, newest first |

Interactive docs are at `http://localhost:8000/docs` while the server runs.

**Why `age_ms` on device events:** the ESP32 has no real-time clock. The dock sends how long ago the event happened and the server computes the timestamp, so events queued during a WiFi drop still get the right time.

### 4.7 React app (`app/`)

- **Role-based screens:** `App.jsx` calls `/me` and renders `PatientHome` or `ProviderHome`.
- **Patient screen:** one status card ("Time for your drops" / "Next drop" / "All done"), one big **Hear reminder** button, captions of what was spoken, and a "3 of 8 drops done today" link to the day's list. Settings (gear button) holds the humor level, high contrast and sign out.
- **Automatic reminders:** the screen polls every 15 s. It speaks automatically when a dose becomes due and again when that dose is resolved (taken or missed).
- **"Tap to start" screen:** iPad Safari blocks sound until the user taps. The first tap unlocks audio and speech, and later automatic reminders reuse the same audio element.
- **Provider screen:** patient list with 7-day stats on the left. On the right, a 14-day stacked bar chart built from plain HTML/CSS (no chart library) and the recent dose list.
- **Auth:** `@auth0/auth0-react` with refresh tokens stored in localStorage. Safari blocks the third-party cookies that silent login would otherwise need. `auth.jsx` hides Auth0 vs dev bypass behind one interface.

**Accessibility choices** (from the README):
- Dark by default; high-contrast mode is pure black, white and yellow.
- Text uses `rem`, and `font: -apple-system-body` makes it follow the iPad's Dynamic Type setting.
- Patient buttons are at least ~88 px tall.
- Every result shows a symbol and a word as well as a color (✓ On time, ✕ Missed, ...).
- The status card is an `aria-live` region, and there is visible focus styling.

### 4.8 Dock firmware (`firmware/main.py`)

- Polls status every 15 s. When a dose is due: red LED on, green off, 3 beeps every 20 s.
- **Lift detection:** the switch is debounced (50 ms), and the bottle must be out of the cup for **1.5 s** to count as a lift, so bumps are ignored. The return is reported when the bottle goes back.
- Lifting the bottle or pressing the big button silences the alarm for that dose.
- Events are queued (max 16) and retried, so WiFi drops don't lose doses.
- No WiFi: red LED blinks slowly.
- HTTPS backends work, but MicroPython doesn't verify certificates. That's fine for a hackathon, not for production.

Pins (also in `hardware/README.md`): green LED GPIO 25, red LED GPIO 26, buzzer GPIO 27, lift switch GPIO 14, silence button GPIO 33.

### 4.9 Evals (`evals/`)

- `cases.json`: 12 cases covering every flag, several drops, eyes and names, two "too frequent" variants.
- `run_evals.py` runs each case at all 3 humor levels (36 reminders; `--repeat N` samples Gemini more) and scores the README's checks: **instruction preserved exactly, tone matches flag, no medical advice, acceptable length, requested humor level**. It uses the same check functions as the live backend.
- Writes `evals/results.md` with the pass-rate table for the README.
- Offline mode (`--offline`) uses only the built-in lines and scores 100% by construction. It only proves the pipeline works. **The README numbers must come from a live run with `GEMINI_API_KEY` set.** The report also shows how many Gemini wrappers were rejected and replaced by fallback lines; report that number too.

### 4.10 Tests (`backend/tests/`)

16 `unittest` tests (no extra packages needed): on-time/late/early boundaries, lift matching (overdue first, upcoming next, windows), due/missed timing, same-time staggering, taper step dates, every flag has a template, every fallback line passes every check, and the guardrails reject medication names, numbers, praise after a missed dose and medical advice.

---

## 5. What was verified, and what was not

| Check | Result |
| --- | --- |
| Backend unit tests | ✅ 16/16 pass |
| All Python (backend, scripts, firmware, evals) compiles | ✅ |
| React app production build (`npm run build`) | ✅ |
| Eval runner (offline mode) | ✅ runs; 36/36 (expected for fallback lines) |
| Schema applied to Tiger Cloud | ❌ not run: needs your `DATABASE_URL` |
| Backend serving real requests / seed script | ❌ not run: needs the database |
| Auth0 login | ❌ needs your tenant |
| Gemini text + TTS | ❌ needs your API key; model names are settings in `.env` in case they change |
| App on a real iPad | ❌ |
| Firmware on an ESP32 | ❌ |

---

## 6. Setup and run

### 6.1 Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env   then fill it in
python -m scripts.init_db         # create tables, hypertables, continuous aggregate
python -m scripts.seed --due-now  # demo data; --due-now makes a dose due right away
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python -m unittest discover -s tests -t .   # tests
```

### 6.2 Auth0 (one-time)

1. **APIs → Create API.** Set the identifier to your `AUTH0_AUDIENCE` (e.g. `https://api.eyespy.local`).
2. **User Management → Roles:** create `patient` and `provider`, and assign them to your test users.
3. **Actions → Login flow:** add this Action so roles appear in the access token:
   ```js
   exports.onExecutePostLogin = async (event, api) => {
     api.accessToken.setCustomClaim("https://eyespy.app/roles", event.authorization?.roles || []);
   };
   ```
4. **Applications → Create → Single Page Application.** Add your app URL(s) (e.g. `http://localhost:5173`) to Allowed Callback URLs, Allowed Logout URLs and Allowed Web Origins. Enable Refresh Token Rotation.
5. Put each test user's `user_id` (the `sub`, e.g. `auth0|abc123`) into `DEMO_PATIENT_SUB` / `DEMO_PROVIDER_SUB` in `backend/.env`, then re-run the seed.

### 6.3 App

```bash
cd app
npm install
copy .env.example .env.local      # fill in Auth0 + VITE_API_BASE_URL
npm run dev                       # serves on http://localhost:5173 and your LAN IP
```

On the iPad, open the URL in Safari, tap **Share → Add to Home Screen**, and open it from the home screen for a full-screen app.

> ⚠️ **Auth0 login needs HTTPS or `localhost`.** The Auth0 SDK refuses to run on `http://192.168.x.x`. To demo on the iPad you can either:
> - set `VITE_DEV_BYPASS_SUB=auth0|demo-patient` and `DEV_AUTH_BYPASS=true` on the backend, for a local network only; or
> - deploy the app to an HTTPS static host and the backend to an HTTPS host. An HTTPS page can't call an HTTP API.
>
> Add the app's origin to `ALLOWED_ORIGINS` in `backend/.env` (CORS).

### 6.4 Dock

```bash
pip install esptool mpremote
# Flash MicroPython (>= 1.20) for ESP32 from micropython.org, then:
cd firmware
copy config_example.py config.py  # WiFi, BACKEND_URL (laptop LAN IP), DEVICE_TOKEN
mpremote cp config.py :config.py
mpremote cp main.py :main.py
mpremote reset
mpremote repl                     # watch the logs
```

**Testing without the dock:** send the dock's requests by hand.

```bash
curl -H "X-Device-Token: <DEVICE_TOKEN>" http://localhost:8000/device/status
curl -X POST -H "X-Device-Token: <DEVICE_TOKEN>" -H "Content-Type: application/json" -d "{\"event\":\"lifted\"}" http://localhost:8000/device/events
```

### 6.5 Evals

```bash
python evals/run_evals.py             # live Gemini if GEMINI_API_KEY is set
python evals/run_evals.py --repeat 3  # more samples
```

Copy the table from `evals/results.md` into the README.

---

## 7. Known limitations (on purpose for a baseline)

- **One cup, several drops:** the dock can't tell which bottle was lifted, so a lift is matched to whichever dose is due. The README's "one slot per medication" future work fixes this.
- **Any unmatched lift is `too_frequent`**, including someone just moving the bottle. The patient hears a gentle "if you were just moving the bottle, no worries" line.
- **In-memory caches** (reminder scripts, TTS audio, materialized days) assume a single backend process. Fine for a demo; use Redis or the database if you scale out.
- **Missed-dose sweep runs on requests**, not on a timer. If nothing calls the API, flags update on the next call.
- **No reminders when the browser tab is closed.** The dock still alarms. Push notifications are future work.
- **Gemini sees the patient's first name** (demo data only). Remove it from the prompt before using any real data.
- **Not a medical device, not HIPAA compliant**, as the README says.

---

## 8. Change history

1. **Backend (Python/FastAPI):** schema, rules, dose tracking, reminder pipeline with guardrails, TTS, Auth0 + device auth, routes, init and seed scripts, unit tests.
2. **Evals:** 12 cases and a runner sharing the backend's checks.
3. **First pass at the client and firmware** in SwiftUI and Arduino C++. **Removed** after the request to use only Python, Java, React, HTML and CSS.
4. **Java:** after discussion, the Python backend was kept and Java is not used.
5. **Replacements:** React web app (`app/`) for the iPad client, MicroPython (`firmware/main.py`) for the dock, and the schema moved from a `.sql` file into `backend/app/schema.py`. CORS added to the backend for the web app.
6. **`.gitignore`:** added entries so secrets (`.env`, `.env.local`, `firmware/config.py`) and build output stay out of git.
7. **Verification:** tests, Python compile check and `npm run build` all pass (see section 5). No git commits or pushes were made.
8. **README.md** created in the repo from the original and updated:
   - Architecture and tech stack now say React, Python/FastAPI and MicroPython.
   - Added a dose-rules table, the guardrails step, the wiring pin map, Auth0 setup, real run commands, the repository structure and known limitations.
   - Eval pass rates and the team list stay TODO.
