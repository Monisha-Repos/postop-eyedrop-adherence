import { useEffect, useState } from "react";
import { formatTime, parseDate } from "../api.js";
import FlagBadge from "../components/FlagBadge.jsx";
import { doseTitle } from "../flags.js";
import AdherenceChart from "./AdherenceChart.jsx";

// Adherence over time for one patient (from the daily_adherence continuous aggregate) plus recent doses.
export default function PatientDetail({ api, patient }) {
  const [days, setDays] = useState([]);
  const [doses, setDoses] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.get(`/provider/patients/${patient.id}/adherence?days=14`),
      api.get(`/provider/patients/${patient.id}/doses?days=3`),
    ])
      .then(([adherence, recent]) => {
        if (cancelled) return;
        setDays(adherence);
        setDoses(recent);
        setError(null);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [api, patient.id]);

  return (
    <>
      <h2>{patient.name}</h2>
      {patient.surgery_date && <p className="muted">Surgery {patient.surgery_date}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <h3>Daily results, last 14 days</h3>
      <AdherenceChart days={days} />

      <h3>Recent doses</h3>
      <ul className="dose-list">
        {doses.map((dose) => (
          <li key={dose.id}>
            <span className="dose-main">
              <strong>{doseTitle(dose)}</strong>
              <span className="muted">
                {parseDate(dose.scheduled_at).toLocaleDateString([], { month: "short", day: "numeric" })}{" "}
                {formatTime(dose.scheduled_at)}
                {dose.lifted_at && ` · lifted ${formatTime(dose.lifted_at)}`}
              </span>
            </span>
            <FlagBadge flag={dose.flag} />
          </li>
        ))}
      </ul>
    </>
  );
}
