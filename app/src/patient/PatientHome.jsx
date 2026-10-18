
import { useCallback, useEffect, useRef, useState } from "react";
import { formatTime } from "../api.js";
import { doseDetail, doseTitle, TAKEN_FLAGS } from "../flags.js";
import {
  playReminder,
  unlockAudio,
  pauseReminder,
  resumeReminder,
  stopReminder,
  snoozeReminder,
  getAvailableVoices,
  getVoiceSettings,
  saveVoiceSettings
} from "../reminderPlayer.js";
import PatientSettings from "./PatientSettings.jsx";
import TodayList from "./TodayList.jsx";

const POLL_MS = 15000;

export default function PatientHome({ api, me, settings }) {
  const [today, setToday] = useState(null);
  const [lastReminder, setLastReminder] = useState(null);
  const [error, setError] = useState(null);
  const [humor, setHumor] = useState(me.humor_level ?? "full");
  const [audioReady, setAudioReady] = useState(false);
  const [sheet, setSheet] = useState(null);
  const [voices, setVoices] = useState([]);
  const [voiceSettings, setVoiceSettings] = useState(getVoiceSettings);
  const [reminderStatus, setReminderStatus] = useState("");

  const audioReadyRef = useRef(false);
  const announcedDoseId = useRef(null);
  const previousDueId = useRef(null);

  const dark = settings.darkMode ?? false;

  const theme = {
    bg: dark ? "#101C24" : "#F3F8F6",
    card: dark ? "#1C2B35" : "#FFFFFF",
    mint: dark ? "#253943" : "#DCEFE8",
    teal: dark ? "#75D8C8" : "#176B63",
    text: dark ? "#F1F7F7" : "#164D49",
    muted: dark ? "#B6C8CD" : "#526B68",
    border: dark ? "#40535D" : "#D5E6DF",
    button: dark ? "#267E77" : "#176B63"
  };

  const cardStyle = {
    background: theme.card,
    border: `1px solid ${theme.border}`,
    borderRadius: 22,
    padding: "clamp(20px, 4vw, 32px)",
    boxShadow: "0 4px 20px rgba(0,0,0,0.05)"
  };

  const buttonStyle = {
    background: theme.button,
    color: "#FFFFFF",
    border: "none",
    borderRadius: 14,
    padding: "16px 22px",
    fontSize: 17,
    fontWeight: 700,
    minHeight: 54,
    cursor: "pointer"
  };

  const headerButtonStyle = {
    background: theme.card,
    color: theme.text,
    border: `1px solid ${theme.border}`,
    borderRadius: 14,
    padding: "12px 15px",
    fontSize: 15,
    fontWeight: 700,
    minHeight: 50,
    cursor: "pointer",
    whiteSpace: "nowrap",
    flexShrink: 0
  };

  const selectStyle = {
    width: "100%",
    padding: 15,
    borderRadius: 12,
    border: `1px solid ${theme.border}`,
    background: theme.mint,
    color: theme.text,
    fontSize: 17,
    marginBottom: 20,
    boxSizing: "border-box"
  };

  useEffect(() => {
    const loadVoices = () => {
      setVoices(getAvailableVoices());
    };

    loadVoices();

    if ("speechSynthesis" in window) {
      window.speechSynthesis.addEventListener(
        "voiceschanged",
        loadVoices
      );

      return () => {
        window.speechSynthesis.removeEventListener(
          "voiceschanged",
          loadVoices
        );
      };
    }
  }, []);

  const updateVoice = (changes) => {
    const updated = saveVoiceSettings(changes);
    setVoiceSettings(updated);
  };

  const hearReminder = useCallback(async () => {
    try {
      const reminder = await api.get("/patient/reminder");
      setLastReminder(reminder);
      await playReminder(reminder, api);
    } catch {
      setError("Couldn't load the reminder.");
    }
  }, [api]);

  const refresh = useCallback(async () => {
    try {
      const fresh = await api.get("/patient/today");
      setToday(fresh);
      setError(null);

      const dueId = fresh.due_dose?.id ?? null;
      const before = previousDueId.current;
      previousDueId.current = dueId;

      if (!audioReadyRef.current) return;

      if (
        dueId !== null &&
        dueId !== announcedDoseId.current
      ) {
        announcedDoseId.current = dueId;
        hearReminder();
      } else if (
        before !== null &&
        dueId !== before
      ) {
        hearReminder();
      }
    } catch {
      setError("Can't reach EyeSpy right now.");
    }
  }, [api, hearReminder]);

  useEffect(() => {
    refresh();

    const timer = setInterval(refresh, POLL_MS);

    return () => clearInterval(timer);
  }, [refresh]);

  const start = () => {
    unlockAudio();
    audioReadyRef.current = true;
    setAudioReady(true);
    refresh();
  };

  const doses = today?.doses ?? [];

  const done = doses.filter((d) =>
    TAKEN_FLAGS.includes(d.flag)
  ).length;

  const scheduled = doses.filter(
    (d) => d.flag !== "too_frequent"
  ).length;

  const progressPercent =
    scheduled > 0
      ? Math.min(100, Math.round((done / scheduled) * 100))
      : 0;

  const handlePlay = async () => {
    unlockAudio();

    try {
      const reminder = await api.get("/patient/reminder");
      setLastReminder(reminder);
      await playReminder(reminder, api);
      setReminderStatus("Reminder started");
    } catch {
      setReminderStatus("Unable to play reminder");
    }
  };

  return (
    <main
      className="patient"
      style={{
        background: theme.bg,
        color: theme.text,
        minHeight: "100vh",
        padding: "clamp(18px, 4vw, 40px)",
        boxSizing: "border-box"
      }}
    >
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          display: "grid",
          gap: 22,
          minWidth: 0
        }}
      >
        {/* HEADER */}
        <header
          className="patient-header"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            flexWrap: "wrap",
            width: "100%",
            minWidth: 0,
            boxSizing: "border-box"
          }}
        >
          {/* LOGO AND WELCOME */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              flex: "1 1 350px",
              minWidth: 0
            }}
          >
            <img
              src="/eyespy-logo.png"
              alt="EyeSpy logo"
              style={{
                width: 82,
                height: 82,
                objectFit: "cover",
                borderRadius: 18,
                flexShrink: 0,
                border: `1px solid ${theme.border}`
              }}
            />

            <div style={{ minWidth: 0 }}>
              <p
                style={{
                  color: theme.teal,
                  fontWeight: 700,
                  fontSize: 15,
                  margin: "0 0 8px"
                }}
              >
                YOUR RECOVERY DASHBOARD
              </p>

              <h1
                style={{
                  color: theme.text,
                  fontSize: "clamp(28px, 5vw, 40px)",
                  lineHeight: 1.2,
                  margin: 0
                }}
              >
                Hello, {me.name}!
              </h1>

              <p
                style={{
                  color: theme.muted,
                  fontSize: 18,
                  lineHeight: 1.6,
                  margin: "12px 0 0"
                }}
              >
                Your eye care routine, made simple.
              </p>
            </div>
          </div>

          {/* DARK MODE AND SETTINGS BUTTONS */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-start",
              gap: 10,
              flexWrap: "wrap",
              maxWidth: "100%",
              minWidth: 0,
              boxSizing: "border-box"
            }}
          >
            <button
              type="button"
              onClick={() => settings.setDarkMode(!dark)}
              aria-pressed={dark}
              style={headerButtonStyle}
            >
              {dark ? "☀️ Light" : "🌙 Dark"}
            </button>

            <button
              type="button"
              className="icon-button"
              onClick={() => setSheet("settings")}
              aria-label="Open settings"
              style={headerButtonStyle}
            >
              ⚙ Settings
            </button>
          </div>
        </header>

        {/* MEDICATION STATUS */}
        <div style={cardStyle}>
          <StatusCard today={today} theme={theme} />
        </div>

        {/* REMINDER CARD */}
        <div
          style={{
            ...cardStyle,
            background: theme.mint
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              marginBottom: 16
            }}
          >
            <div
              style={{
                width: 58,
                height: 58,
                borderRadius: 16,
                background: theme.card,
                display: "grid",
                placeItems: "center",
                fontSize: 28,
                flexShrink: 0
              }}
            >
              🔊
            </div>

            <div>
              <h2
                style={{
                  color: theme.text,
                  fontSize: 23,
                  margin: "0 0 6px"
                }}
              >
                Hear Your Reminder
              </h2>

              <p
                style={{
                  color: theme.muted,
                  fontSize: 16,
                  margin: 0,
                  lineHeight: 1.6
                }}
              >
                Listen to your eye-drop instructions.
              </p>
            </div>
          </div>

          <button
            type="button"
            className="big-button"
            onClick={handlePlay}
            style={{
              ...buttonStyle,
              width: "100%"
            }}
          >
            🔊 Play Eye-Drop Reminder
          </button>

          {lastReminder && (
            <div
              className="caption"
              aria-live="polite"
              style={{
                background: theme.card,
                color: theme.text,
                padding: 18,
                borderRadius: 14,
                marginTop: 18,
                fontSize: 17,
                lineHeight: 1.7
              }}
            >
              {lastReminder.script}
            </div>
          )}
        </div>

        {/* VOICE CONTROLS */}
        <div style={cardStyle}>
          <h2
            style={{
              color: theme.text,
              fontSize: 27,
              marginTop: 0
            }}
          >
            🎙️ Voice & Reminder Controls
          </h2>

          <p
            style={{
              color: theme.muted,
              fontSize: 17,
              lineHeight: 1.6
            }}
          >
            Choose your favorite voice and control your reminders.
          </p>

          <label
            htmlFor="eyespy-voice"
            style={{
              display: "block",
              color: theme.text,
              fontWeight: 700,
              marginBottom: 10
            }}
          >
            Choose a Voice
          </label>

          <select
            id="eyespy-voice"
            value={voiceSettings.voiceURI}
            onChange={(event) => {
              updateVoice({
                voiceURI: event.target.value,
                preferBrowserVoice: true
              });
            }}
            style={selectStyle}
          >
            <option value="">Default device voice</option>

            {voices.map((voice) => (
              <option
                key={voice.voiceURI}
                value={voice.voiceURI}
              >
                {voice.name} ({voice.lang})
              </option>
            ))}
          </select>

          <label
            htmlFor="eyespy-speed"
            style={{
              display: "block",
              color: theme.text,
              fontWeight: 700,
              marginBottom: 10
            }}
          >
            Speaking Speed
          </label>

          <select
            id="eyespy-speed"
            value={voiceSettings.rate}
            onChange={(event) => {
              updateVoice({
                rate: Number(event.target.value),
                preferBrowserVoice: true
              });
            }}
            style={selectStyle}
          >
            <option value={0.7}>Slow</option>
            <option value={0.85}>Gentle</option>
            <option value={1}>Normal</option>
            <option value={1.2}>Fast</option>
          </select>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(140px, 1fr))",
              gap: 12
            }}
          >
            <button
              type="button"
              style={buttonStyle}
              onClick={handlePlay}
            >
              ▶ Play
            </button>

            <button
              type="button"
              style={buttonStyle}
              onClick={() => {
                pauseReminder();
                setReminderStatus("Reminder paused");
              }}
            >
              ⏸ Pause
            </button>

            <button
              type="button"
              style={buttonStyle}
              onClick={() => {
                resumeReminder();
                setReminderStatus("Resuming reminder");
              }}
            >
              ⏯ Resume
            </button>

            <button
              type="button"
              style={{
                ...buttonStyle,
                background: "#A94442"
              }}
              onClick={() => {
                stopReminder();
                setReminderStatus("Reminder stopped");
              }}
            >
              ■ Stop
            </button>

            <button
              type="button"
              style={{
                ...buttonStyle,
                background: "#526B68",
                gridColumn: "1 / -1"
              }}
              onClick={() => {
                const wasScheduled = snoozeReminder(5);

                setReminderStatus(
                  wasScheduled
                    ? "Reminder snoozed for 5 minutes"
                    : "Play a reminder before snoozing"
                );
              }}
            >
              💤 Snooze 5 Minutes
            </button>
          </div>

          <p
            role="status"
            aria-live="polite"
            style={{
              color: theme.teal,
              fontWeight: 700,
              marginTop: 16
            }}
          >
            {reminderStatus}
          </p>

          <p
            style={{
              color: theme.muted,
              fontSize: 14,
              lineHeight: 1.6
            }}
          >
            Snooze delays the spoken reminder only.
            It does not change your prescribed eye-drop schedule.
            Keep this app open for snoozed playback.
          </p>
        </div>

        {/* TODAY'S EYE DROPS */}
        <div style={cardStyle}>
          <h2
            style={{
              color: theme.text,
              fontSize: 24,
              margin: "0 0 10px"
            }}
          >
            Today's Eye Drops
          </h2>

          <p
            style={{
              color: theme.muted,
              fontSize: 17,
              lineHeight: 1.6
            }}
          >
            Keep track of your scheduled eye drops.
          </p>

          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 10,
              margin: "18px 0"
            }}
          >
            <strong
              style={{
                fontSize: 36,
                color: theme.teal
              }}
            >
              {done}
            </strong>

            <span
              style={{
                color: theme.muted,
                fontSize: 18
              }}
            >
              of {scheduled} drops completed
            </span>
          </div>

          <div
            role="progressbar"
            aria-label="Today's eye-drop progress"
            aria-valuemin={0}
            aria-valuemax={scheduled}
            aria-valuenow={done}
            style={{
              height: 14,
              background: theme.mint,
              borderRadius: 20,
              overflow: "hidden",
              marginBottom: 22
            }}
          >
            <div
              style={{
                width: `${progressPercent}%`,
                height: "100%",
                background: theme.teal,
                borderRadius: 20
              }}
            />
          </div>

          <button
            type="button"
            className="text-button progress"
            onClick={() => setSheet("today")}
            style={{
              ...buttonStyle,
              width: "100%"
            }}
          >
            View Today's Schedule →
          </button>
        </div>

        {/* ERROR MESSAGE */}
        {error && (
          <p
            className="error"
            role="alert"
            style={{
              background: "#FFF1F0",
              color: "#B42318",
              padding: 16,
              borderRadius: 12
            }}
          >
            {error}
          </p>
        )}

        {/* OPENING SCREEN */}
        {!audioReady && (
          <div
            className="start-overlay"
            style={{
              background: theme.bg,
              color: theme.text,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 20,
              padding: 24,
              textAlign: "center"
            }}
          >
            <img
              src="/eyespy-logo.png"
              alt="EyeSpy Healthcare Cataract Recovery"
              style={{
                width: "min(80vw, 420px)",
                maxWidth: "100%",
                aspectRatio: "16 / 9",
                objectFit: "contain",
                borderRadius: 24,
                boxShadow:
                  "0 12px 35px rgba(22, 77, 73, 0.12)"
              }}
            />

            <h1
              style={{
                color: theme.text,
                fontSize: "clamp(28px, 5vw, 42px)",
                margin: 0
              }}
            >
              Welcome to EyeSpy
            </h1>

            <p
              style={{
                color: theme.muted,
                fontSize: 19,
                lineHeight: 1.7,
                maxWidth: 460,
                margin: 0
              }}
            >
              Your companion for a comfortable cataract recovery.
            </p>

            <button
              type="button"
              className="big-button"
              onClick={start}
              style={{
                ...buttonStyle,
                width: "min(100%, 360px)",
                marginTop: 12,
                fontSize: 21,
                minHeight: 66
              }}
            >
              Tap to Start →
            </button>

            <p
              style={{
                color: theme.muted,
                fontSize: 15,
                maxWidth: 440,
                margin: 0
              }}
            >
              This also enables spoken eye-drop reminders.
            </p>
          </div>
        )}

        {/* SETTINGS PANEL */}
        {sheet === "settings" && (
          <PatientSettings
            api={api}
            humor={humor}
            onHumorChange={setHumor}
            settings={settings}
            onClose={() => setSheet(null)}
          />
        )}

        {/* MEDICATION SCHEDULE */}
        {sheet === "today" && (
          <TodayList
            doses={doses}
            onClose={() => setSheet(null)}
          />
        )}
      </div>
    </main>
  );
}

function StatusCard({ today, theme }) {
  let content;

  if (!today) {
    content = (
      <p style={{ color: theme.muted, fontSize: 18 }}>
        Loading your eye-drop schedule…
      </p>
    );
  } else if (today.due_dose) {
    const due = today.due_dose;

    content = (
      <>
        <p
          className="status-label accent"
          style={{
            color: theme.teal,
            fontWeight: 700,
            fontSize: 17
          }}
        >
          🔔 TIME FOR YOUR EYE DROPS
        </p>

        <p
          className="status-med"
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: theme.text,
            margin: "12px 0"
          }}
        >
          {doseTitle(due)}
        </p>

        <p
          className="status-detail"
          style={{
            color: theme.muted,
            fontSize: 19,
            lineHeight: 1.7
          }}
        >
          {doseDetail(due)}
        </p>
      </>
    );
  } else if (today.next_dose) {
    const next = today.next_dose;

    content = (
      <>
        <p
          className="status-label muted"
          style={{
            color: theme.teal,
            fontWeight: 700,
            fontSize: 17
          }}
        >
          YOUR NEXT EYE DROP
        </p>

        <p
          className="status-med"
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: theme.text,
            margin: "12px 0"
          }}
        >
          {doseTitle(next)}
        </p>

        <p
          className="status-detail"
          style={{
            color: theme.muted,
            fontSize: 19,
            lineHeight: 1.7
          }}
        >
          {formatTime(next.scheduled_at)}
          {" · "}
          {doseDetail(next)}
        </p>
      </>
    );
  } else {
    content = (
      <p
        className="status-med done"
        style={{
          fontSize: 26,
          fontWeight: 700,
          color: theme.teal
        }}
      >
        ✓ All done for today
      </p>
    );
  }

  return (
    <section
      className="status-card"
      aria-live="polite"
      style={{
        background: "transparent",
        border: "none",
        padding: 0,
        boxShadow: "none",
        color: theme.text
      }}
    >
      {content}
    </section>
  );
}
