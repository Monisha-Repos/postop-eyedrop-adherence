import { useCallback, useEffect, useState } from "react";
import PatientDetail from "./PatientDetail.jsx";

const pct = (value) => (value === null || value === undefined ? "–" : `${value}%`);

// Provider screen: patient list on the left, adherence detail on the right.
export default function ProviderHome({ api, me, signOut }) {
  const [patients, setPatients] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setPatients(await api.get("/provider/patients"));
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  const selected = patients.find((p) => p.id === selectedId);

  return (
    <div className="provider">
      <aside className="patient-list">
        <header className="list-header">
          <h1>My patients</h1>
          <button className="text-button" onClick={signOut}>Sign out</button>
        </header>
        <p className="muted small">{me.name} · last 7 days</p>
        {error && <p className="error" role="alert">{error}</p>}
        <ul>
          {patients.map((p) => (
            <li key={p.id}>
              <button
                className={`patient-row ${p.id === selectedId ? "selected" : ""}`}
                onClick={() => setSelectedId(p.id)}
                aria-current={p.id === selectedId}
              >
                <strong>{p.name}</strong>
                <span className="row-stats">
                  <span>Taken {pct(p.taken_pct_7d)}</span>
                  <span>On time {pct(p.on_time_pct_7d)}</span>
                  {p.missed_7d > 0 && <span className="flag-text-missed">✕ {p.missed_7d} missed</span>}
                </span>
              </button>
            </li>
          ))}
        </ul>
        <button className="text-button" onClick={load}>Refresh</button>
      </aside>

      <section className="patient-detail">
        {selected ? (
          <PatientDetail key={selected.id} api={api} patient={selected} />
        ) : (
          <p className="muted center-text">Select a patient</p>
        )}
      </section>
    </div>
  );
}
