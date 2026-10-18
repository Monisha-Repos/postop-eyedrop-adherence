
import { useEffect, useState } from "react";
import { formatTime, parseDate } from "../api.js";
import FlagBadge from "../components/FlagBadge.jsx";
import { doseTitle } from "../flags.js";
import AdherenceChart from "./AdherenceChart.jsx";

function EyePhoto({ api, patientId, entry }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl = "";

    setUrl("");
    setError(false);

    if (!entry.has_image) {
      return () => {};
    }

    async function loadImage() {
      try {
        const blob = await api.blob(
          `/provider/patients/${patientId}` +
          `/eye-analyses/${entry.id}/image`
        );

        if (cancelled) return;

        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch {
        if (!cancelled) setError(true);
      }
    }

    loadImage();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [api, patientId, entry.id, entry.has_image]);

  if (!entry.has_image) {
    return <p className="muted">No photo attached.</p>;
  }

  if (error) {
    return <p className="muted">Photo unavailable.</p>;
  }

  if (!url) {
    return <p className="muted">Loading photo...</p>;
  }

  return (
    <img
      src={url}
      alt={`Eye photo from ${new Date(
        entry.created_at
      ).toLocaleDateString()}`}
      style={{
        width: "100%",
        height: 200,
        objectFit: "contain",
        borderRadius: 12,
        background: "#eef5f1",
      }}
    />
  );
}

function AnalysisDetails({ analysis }) {
  if (!analysis) {
    return <p className="muted">Photo saved without AI analysis.</p>;
  }

  let data = analysis;

  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch {
      return <p style={{ whiteSpace: "pre-wrap" }}>{data}</p>;
    }
  }

  if (!data || typeof data !== "object") {
    return <p className="muted">No analysis available.</p>;
  }

  return (
    <div>
      {[
        ["Redness", data.redness],
        ["Irritation", data.irritation],
        ["Cloudiness", data.cloudiness],
        ["Image Quality", data.image_quality],
        ["Summary", data.summary],
        ["Recommendation", data.recommendation],
      ].map(([label, value]) => (
        <p key={label} style={{ margin: "8px 0" }}>
          <strong>{label}: </strong>
          {typeof value === "string"
            ? value || "Not assessed"
            : value == null
              ? "Not assessed"
              : JSON.stringify(value)}
        </p>
      ))}
    </div>
  );
}

export default function PatientDetail({ api, patient }) {
  const [days, setDays] = useState([]);
  const [doses, setDoses] = useState([]);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError("");
    setDays([]);
    setDoses([]);
    setAnalyses([]);

    async function load() {
      const requests = await Promise.allSettled([
        api.get(
          `/provider/patients/${patient.id}/adherence?days=14`
        ),
        api.get(
          `/provider/patients/${patient.id}/doses?days=3`
        ),
        api.get(
          `/provider/patients/${patient.id}/eye-analyses`
        ),
      ]);

      if (cancelled) return;

      const [adherence, recent, history] = requests;
      const errors = [];

      if (adherence.status === "fulfilled") {
        setDays(adherence.value);
      } else {
        errors.push("Could not load adherence.");
      }

      if (recent.status === "fulfilled") {
        setDoses(recent.value);
      } else {
        errors.push("Could not load recent doses.");
      }

      if (history.status === "fulfilled") {
        setAnalyses(history.value);
      } else {
        errors.push("Could not load eye-photo history.");
      }

      setError(errors.join(" "));
      setLoading(false);
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [api, patient.id]);

  return (
    <div style={{ display: "grid", gap: 28 }}>
      <section>
        <h2>{patient.name}</h2>

        {patient.surgery_date && (
          <p className="muted">
            Surgery: {patient.surgery_date}
          </p>
        )}
      </section>

      {loading && (
        <p className="muted">Loading patient recovery data...</p>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <section>
        <h3>Eye Photo History & AI Observations</h3>

        <p className="muted">
          Photos uploaded by the patient, with preliminary
          AI-generated observations. Not a medical diagnosis.
        </p>

        {!loading && analyses.length === 0 && (
          <div
            style={{
              padding: 24,
              border: "1px solid #d9e9e3",
              borderRadius: 16,
              textAlign: "center",
            }}
          >
            <p style={{ fontSize: 32 }}>📷</p>
            <strong>No saved eye photos yet</strong>
            <p className="muted">
              Patient uploads will appear here automatically.
            </p>
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 16,
            marginTop: 16,
          }}
        >
          {analyses.map((entry) => (
            <article
              key={entry.id}
              style={{
                border: "1px solid #d9e9e3",
                borderRadius: 16,
                padding: 16,
              }}
            >
              <EyePhoto
                api={api}
                patientId={patient.id}
                entry={entry}
              />

              <p className="muted">
                {new Date(entry.created_at).toLocaleString()}
              </p>

              <h4>AI Observation</h4>

              <AnalysisDetails analysis={entry.analysis} />
            </article>
          ))}
        </div>
      </section>

      <section>
        <h3>Daily Results — Last 14 Days</h3>
        <AdherenceChart days={days} />
      </section>

      <section>
        <h3>Recent Eye-Drop Doses</h3>

        {!loading && doses.length === 0 && (
          <p className="muted">No recent doses.</p>
        )}

        <ul className="dose-list">
          {doses.map((dose) => (
            <li key={dose.id}>
              <span className="dose-main">
                <strong>{doseTitle(dose)}</strong>

                <span className="muted">
                  {parseDate(
                    dose.scheduled_at
                  ).toLocaleDateString([], {
                    month: "short",
                    day: "numeric",
                  })}{" "}
                  {formatTime(dose.scheduled_at)}

                  {dose.lifted_at &&
                    ` · lifted ${formatTime(
                      dose.lifted_at
                    )}`}
                </span>
              </span>

              <FlagBadge flag={dose.flag} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
