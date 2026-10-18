
import { useCallback, useEffect, useMemo, useState } from "react";
import PatientDetail from "./PatientDetail.jsx";

const colors = {
  background: "#F3F8F6",
  card: "#FFFFFF",
  teal: "#176B63",
  dark: "#164D49",
  muted: "#526B68",
  border: "#DCE6E2",
  mint: "#DCEFE8",
  warning: "#9A5B17",
  warningBg: "#FFF2DA",
};

const pct = (value) =>
  value === null || value === undefined ? "—" : `${value}%`;

export default function ProviderHome({ api, me, signOut }) {
  const [patients, setPatients] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const result = await api.get("/provider/patients");
      const list = Array.isArray(result) ? result : [];

      setPatients(list);
      setSelectedId((previous) =>
        list.some((patient) => patient.id === previous)
          ? previous
          : null
      );
      setError(null);
    } catch (err) {
      setError(err.message || "Unable to load patients.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredPatients = useMemo(
    () =>
      patients.filter((patient) =>
        String(patient.name || "")
          .toLowerCase()
          .includes(search.toLowerCase().trim())
      ),
    [patients, search]
  );

  const selected = patients.find(
    (patient) => patient.id === selectedId
  );

  const needsReview = patients.filter(
    (patient) => Number(patient.missed_7d || 0) > 0
  ).length;

  const adherenceValues = patients
    .map((patient) => patient.taken_pct_7d)
    .filter(
      (value) =>
        value !== null &&
        value !== undefined &&
        Number.isFinite(Number(value))
    )
    .map(Number);

  const averageAdherence = adherenceValues.length
    ? Math.round(
        adherenceValues.reduce((sum, value) => sum + value, 0) /
          adherenceValues.length
      )
    : null;

  const card = {
    background: colors.card,
    border: `1px solid ${colors.border}`,
    borderRadius: 20,
    boxShadow: "0 5px 22px rgba(22,77,73,0.04)",
  };

  const button = {
    border: `1px solid ${colors.border}`,
    borderRadius: 12,
    background: colors.card,
    color: colors.dark,
    padding: "12px 18px",
    fontSize: 15,
    fontWeight: 700,
    cursor: "pointer",
    minHeight: 46,
  };

  return (
    <main
      className="provider"
      style={{
        display: "block",
        minHeight: "100vh",
        width: "100%",
        maxWidth: "none",
        margin: 0,
        padding: 0,
        background: colors.background,
        color: colors.dark,
        boxSizing: "border-box",
      }}
    >
      {/* Top navigation */}
      <header
        style={{
          background: colors.card,
          borderBottom: `1px solid ${colors.border}`,
          padding: "16px clamp(20px, 5vw, 65px)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 20,
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 15,
          }}
        >
          <img
            src="/eyespy-logo.png"
            alt="EyeSpy AI logo"
            style={{
              width: 64,
              height: 64,
              objectFit: "cover",
              borderRadius: 14,
            }}
          />

          <div>
            <h1
              style={{
                margin: 0,
                fontSize: 25,
                color: colors.dark,
              }}
            >
              EyeSpy AI
            </h1>
            <p
              style={{
                margin: "4px 0 0",
                color: colors.muted,
                fontSize: 14,
              }}
            >
              Doctor Portal
            </p>
          </div>
        </div>

        <button type="button" onClick={signOut} style={button}>
          Sign Out
        </button>
      </header>

      <div
        style={{
          maxWidth: 1300,
          margin: "0 auto",
          padding: "32px clamp(16px, 4vw, 40px) 70px",
        }}
      >
        {/* Welcome */}
        <section style={{ marginBottom: 28 }}>
          <p
            style={{
              color: colors.teal,
              fontWeight: 800,
              letterSpacing: 1,
              fontSize: 13,
              margin: "0 0 10px",
            }}
          >
            YOUR DOCTOR DASHBOARD
          </p>

          <h2
            style={{
              fontSize: "clamp(28px, 4vw, 38px)",
              margin: "0 0 12px",
              color: colors.dark,
            }}
          >
            Welcome, {me?.name || "Doctor"}!
          </h2>

          <p
            style={{
              fontSize: 17,
              lineHeight: 1.6,
              color: colors.muted,
              margin: 0,
            }}
          >
            Review your patients' recovery progress and
            eye-drop adherence.
          </p>
        </section>

        {/* Statistics */}
        <section
          aria-label="Patient statistics"
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(210px, 1fr))",
            gap: 16,
            marginBottom: 28,
          }}
        >
          {[
            {
              icon: "👥",
              label: "Total Patients",
              value: patients.length,
              detail: "Assigned to your account",
            },
            {
              icon: "💧",
              label: "Average Adherence",
              value: pct(averageAdherence),
              detail: "Eye drops taken · last 7 days",
            },
            {
              icon: "📋",
              label: "Missed-Dose Follow-Up",
              value: needsReview,
              detail: "Patients with missed doses",
            },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                ...card,
                padding: 24,
              }}
            >
              <div style={{ fontSize: 30, marginBottom: 12 }}>
                {stat.icon}
              </div>

              <p
                style={{
                  color: colors.muted,
                  fontSize: 15,
                  margin: "0 0 10px",
                }}
              >
                {stat.label}
              </p>

              <strong
                style={{
                  display: "block",
                  fontSize: 34,
                  color: colors.dark,
                  marginBottom: 8,
                }}
              >
                {stat.value}
              </strong>

              <p
                style={{
                  color: colors.muted,
                  fontSize: 13,
                  margin: 0,
                }}
              >
                {stat.detail}
              </p>
            </div>
          ))}
        </section>

        {/* Main patient management area */}
        <section
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(min(100%, 340px), 1fr))",
            gap: 20,
            alignItems: "start",
          }}
        >
          {/* Patient list */}
          <div
            className="patient-list"
            style={{
              ...card,
              padding: 22,
              minWidth: 0,
              width: "100%",
              boxSizing: "border-box",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 12,
                marginBottom: 18,
                flexWrap: "wrap",
              }}
            >
              <div>
                <h3
                  style={{
                    fontSize: 23,
                    margin: "0 0 5px",
                    color: colors.dark,
                  }}
                >
                  My Patients
                </h3>

                <p
                  style={{
                    color: colors.muted,
                    margin: 0,
                    fontSize: 14,
                  }}
                >
                  {patients.length} patient records
                </p>
              </div>

              <button
                type="button"
                onClick={load}
                disabled={loading}
                style={button}
              >
                {loading ? "Loading..." : "↻ Refresh"}
              </button>
            </div>

            <label
              htmlFor="doctor-patient-search"
              style={{
                display: "block",
                fontSize: 14,
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              Search patients
            </label>

            <input
              id="doctor-patient-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by patient name..."
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "14px 16px",
                borderRadius: 12,
                border: `1px solid ${colors.border}`,
                background: "#FFFFFF",
                color: colors.dark,
                fontSize: 16,
                marginBottom: 20,
              }}
            />

            {error && (
              <p
                role="alert"
                style={{
                  padding: 14,
                  borderRadius: 12,
                  background: "#FFF1F0",
                  color: "#B42318",
                }}
              >
                {error}
              </p>
            )}

            {loading && patients.length === 0 && (
              <p style={{ color: colors.muted }}>
                Loading patient records...
              </p>
            )}

            {!loading &&
              !error &&
              filteredPatients.length === 0 && (
                <p style={{ color: colors.muted }}>
                  {search
                    ? "No patients match your search."
                    : "No patients assigned yet."}
                </p>
              )}

            <ul
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                display: "grid",
                gap: 12,
              }}
            >
              {filteredPatients.map((patient) => {
                const isSelected = selectedId === patient.id;
                const missed = Number(patient.missed_7d || 0);

                return (
                  <li key={patient.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(patient.id)}
                      aria-pressed={isSelected}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        gap: 13,
                        textAlign: "left",
                        background: isSelected
                          ? colors.mint
                          : colors.card,
                        border: isSelected
                          ? `2px solid ${colors.teal}`
                          : `1px solid ${colors.border}`,
                        borderRadius: 15,
                        padding: 15,
                        color: colors.dark,
                        cursor: "pointer",
                        boxSizing: "border-box",
                      }}
                    >
                      <span
                        aria-hidden="true"
                        style={{
                          width: 46,
                          height: 46,
                          borderRadius: "50%",
                          background: colors.mint,
                          color: colors.teal,
                          display: "grid",
                          placeItems: "center",
                          fontSize: 20,
                          fontWeight: 800,
                          flexShrink: 0,
                        }}
                      >
                        {(patient.name || "P")
                          .charAt(0)
                          .toUpperCase()}
                      </span>

                      <span style={{ flex: 1, minWidth: 0 }}>
                        <strong
                          style={{
                            display: "block",
                            fontSize: 17,
                            marginBottom: 7,
                          }}
                        >
                          {patient.name}
                        </strong>

                        <span
                          style={{
                            display: "block",
                            color: colors.muted,
                            fontSize: 13,
                            marginBottom: 5,
                          }}
                        >
                          Taken: {pct(patient.taken_pct_7d)}
                        </span>

                        <span
                          style={{
                            display: "block",
                            color: colors.muted,
                            fontSize: 13,
                          }}
                        >
                          On time: {pct(patient.on_time_pct_7d)}
                        </span>

                        {missed > 0 && (
                          <span
                            style={{
                              display: "inline-block",
                              marginTop: 9,
                              background: colors.warningBg,
                              color: colors.warning,
                              borderRadius: 8,
                              padding: "5px 9px",
                              fontSize: 12,
                              fontWeight: 700,
                            }}
                          >
                            {missed} missed dose
                            {missed === 1 ? "" : "s"}
                          </span>
                        )}
                      </span>

                      <span
                        aria-hidden="true"
                        style={{
                          color: colors.teal,
                          fontSize: 23,
                        }}
                      >
                        ›
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Patient detail */}
          <div
            className="patient-detail"
            style={{
              ...card,
              padding: "clamp(16px, 3vw, 28px)",
              minWidth: 0,
              width: "100%",
              boxSizing: "border-box",
              overflowWrap: "anywhere",
            }}
          >
            {selected ? (
              <>
                <div
                  style={{
                    marginBottom: 20,
                    paddingBottom: 16,
                    borderBottom: `1px solid ${colors.border}`,
                  }}
                >
                  <p
                    style={{
                      color: colors.teal,
                      fontSize: 13,
                      fontWeight: 800,
                      letterSpacing: 1,
                      margin: "0 0 8px",
                    }}
                  >
                    PATIENT RECORD
                  </p>

                  <h3
                    style={{
                      color: colors.dark,
                      fontSize: 24,
                      margin: 0,
                    }}
                  >
                    {selected.name}
                  </h3>
                </div>

                <PatientDetail
                  key={selected.id}
                  api={api}
                  patient={selected}
                />
              </>
            ) : (
              <div
                style={{
                  minHeight: 340,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  gap: 14,
                  padding: 20,
                }}
              >
                <div style={{ fontSize: 56 }}>🩺</div>

                <h3
                  style={{
                    fontSize: 24,
                    color: colors.dark,
                    margin: 0,
                  }}
                >
                  Select a Patient
                </h3>

                <p
                  style={{
                    fontSize: 16,
                    color: colors.muted,
                    lineHeight: 1.7,
                    maxWidth: 340,
                    margin: 0,
                  }}
                >
                  Choose a patient from the list to review
                  their recovery progress and medication
                  adherence.
                </p>
              </div>
            )}
          </div>
        </section>

        <p
          style={{
            color: colors.muted,
            fontSize: 13,
            lineHeight: 1.6,
            marginTop: 30,
            textAlign: "center",
          }}
        >
          EyeSpy AI is a recovery support prototype.
          AI-generated eye observations are not medical diagnoses.
        </p>
      </div>
    </main>
  );
}
