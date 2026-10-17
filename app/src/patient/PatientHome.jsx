import { useCallback, useEffect, useRef, useState } from "react";
import { formatTime } from "../api.js";
import { doseDetail, doseTitle, TAKEN_FLAGS } from "../flags.js";
import { playReminder, unlockAudio } from "../reminderPlayer.js";
import PatientSettings from "./PatientSettings.jsx";
import TodayList from "./TodayList.jsx";

const POLL_MS = 15000; // keeps the screen roughly in step with the dock

// Patient screen: one status card and one big action ("Hear reminder").
export default function PatientHome({ api, me, settings }) {
  const [today, setToday] = useState(null);
  const [lastReminder, setLastReminder] = useState(null);
  const [error, setError] = useState(null);
  const [humor, setHumor] = useState(me.humor_level ?? "full");
  const [audioReady, setAudioReady] = useState(false);
  const [sheet, setSheet] = useState(null); // "settings" | "today" | null

  const audioReadyRef = useRef(false);
  const announcedDoseId = useRef(null); // due dose already spoken for, so it isn't repeated every poll
  const previousDueId = useRef(null);

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
      if (!audioReadyRef.current) return; // Safari can't play sound before the first tap

      if (dueId !== null && dueId !== announcedDoseId.current) {
        // A dose just became due: speak the reminder without a tap.
        announcedDoseId.current = dueId;
        hearReminder();
      } else if (before !== null && dueId !== before) {
        // The due dose was just taken (or became missed): speak the result.
        hearReminder();
      }
    } catch {
      setError("Can't reach Eye Spy right now. Your dock still keeps time.");
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
  const done = doses.filter((d) => TAKEN_FLAGS.includes(d.flag)).length;
  const scheduled = doses.filter((d) => d.flag !== "too_frequent").length;

  return (
    <main className="patient">
      <header className="patient-header">
        <h1>Hello, {me.name}</h1>
        <button className="icon-button" onClick={() => setSheet("settings")} aria-label="Settings">⚙</button>
      </header>

      <StatusCard today={today} />

      <button className="big-button" onClick={hearReminder}>
        <span aria-hidden="true">🔊</span> Hear reminder
      </button>

      {/* Captions for what was just spoken. */}
      {lastReminder && <p className="caption">{lastReminder.script}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <button className="text-button progress" onClick={() => setSheet("today")}>
        {done} of {scheduled} drops done today ›
      </button>

      {!audioReady && (
        <button className="start-overlay" onClick={start}>
          <span className="start-title">Tap to start</span>
          <span>so Eye Spy can speak your reminders</span>
        </button>
      )}

      {sheet === "settings" && (
        <PatientSettings
          api={api}
          humor={humor}
          onHumorChange={setHumor}
          settings={settings}
          onClose={() => setSheet(null)}
        />
      )}
      {sheet === "today" && <TodayList doses={doses} onClose={() => setSheet(null)} />}
    </main>
  );
}

function StatusCard({ today }) {
  let content;
  if (!today) {
    content = <p className="muted">Loading…</p>;
  } else if (today.due_dose) {
    const due = today.due_dose;
    content = (
      <>
        <p className="status-label accent">🔔 Time for your drops</p>
        <p className="status-med">{doseTitle(due)}</p>
        <p className="status-detail">{doseDetail(due)}</p>
      </>
    );
  } else if (today.next_dose) {
    const next = today.next_dose;
    content = (
      <>
        <p className="status-label muted">Next drop</p>
        <p className="status-med">{doseTitle(next)}</p>
        <p className="status-detail">{formatTime(next.scheduled_at)} · {doseDetail(next)}</p>
      </>
    );
  } else {
    content = <p className="status-med done">✓ All done for today</p>;
  }
  return (
    <section className="status-card" aria-live="polite">
      {content}
    </section>
  );
}
