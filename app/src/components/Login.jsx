
import { useState } from "react";

export default function Login({ onSignIn, onSignOut, error }) {
  const [role, setRole] = useState("patient");

  const colors = {
    background: "#F3F8F6",
    white: "#FFFFFF",
    teal: "#176B63",
    dark: "#164D49",
    muted: "#526B68",
    border: "#D5E6DF",
    selected: "#DCEFE8",
  };

  const roleStyle = (selected) => ({
    flex: "1 1 180px",
    minWidth: 0,
    padding: "25px 15px",
    borderRadius: 18,
    border: selected
      ? `2px solid ${colors.teal}`
      : `2px solid ${colors.border}`,
    background: selected ? colors.selected : colors.white,
    color: colors.dark,
    cursor: "pointer",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
  });

  return (
    <main
      className="login"
      style={{
        minHeight: "100vh",
        background: colors.background,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: 24,
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          background: colors.white,
          border: `1px solid ${colors.border}`,
          borderRadius: 28,
          padding: "clamp(24px, 5vw, 45px)",
          width: "100%",
          maxWidth: 550,
          textAlign: "center",
          boxShadow: "0 15px 50px rgba(22,77,73,0.1)",
          boxSizing: "border-box",
        }}
      >
        <img
          src="/eyespy-logo.png"
          alt="EyeSpy AI logo"
          style={{
            width: "min(100%, 220px)",
            height: "auto",
            borderRadius: 20,
            marginBottom: 18,
          }}
        />

        <h1
          style={{
            color: colors.dark,
            fontSize: 34,
            margin: "0 0 10px",
          }}
        >
          Welcome to EyeSpy AI
        </h1>

        <p
          style={{
            color: colors.muted,
            fontSize: 17,
            marginBottom: 28,
          }}
        >
          Your cataract recovery companion
        </p>

        {error ? (
          <>
            <p
              role="alert"
              style={{
                color: "#B42318",
                background: "#FFF1F0",
                padding: 16,
                borderRadius: 12,
              }}
            >
              {error}
            </p>

            <button
              type="button"
              onClick={onSignOut}
              style={{
                width: "100%",
                padding: 17,
                background: colors.teal,
                color: colors.white,
                border: "none",
                borderRadius: 14,
                fontSize: 17,
                cursor: "pointer",
              }}
            >
              Sign Out and Try Again
            </button>
          </>
        ) : (
          <>
            <h2
              style={{
                fontSize: 20,
                color: colors.dark,
                marginBottom: 20,
              }}
            >
              Choose your account
            </h2>

            <div
              role="group"
              aria-label="Choose account type"
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 16,
                marginBottom: 28,
              }}
            >
              <button
                type="button"
                aria-pressed={role === "patient"}
                onClick={() => setRole("patient")}
                style={roleStyle(role === "patient")}
              >
                <span style={{ fontSize: 42 }}>👤</span>
                <strong style={{ fontSize: 21 }}>Patient</strong>
                <span
                  style={{
                    color: colors.muted,
                    fontSize: 14,
                    lineHeight: 1.5,
                  }}
                >
                  Eye-drop reminders and recovery journal
                </span>
              </button>

              <button
                type="button"
                aria-pressed={role === "doctor"}
                onClick={() => setRole("doctor")}
                style={roleStyle(role === "doctor")}
              >
                <span style={{ fontSize: 42 }}>🩺</span>
                <strong style={{ fontSize: 21 }}>Doctor</strong>
                <span
                  style={{
                    color: colors.muted,
                    fontSize: 14,
                    lineHeight: 1.5,
                  }}
                >
                  Patient records and recovery monitoring
                </span>
              </button>
            </div>

            <button
              type="button"
              onClick={() => onSignIn(role)}
              style={{
                width: "100%",
                minHeight: 60,
                padding: "17px 22px",
                background: colors.teal,
                color: colors.white,
                border: "none",
                borderRadius: 14,
                fontSize: 18,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {role === "patient"
                ? "Continue as Patient →"
                : "Continue as Doctor →"}
            </button>

            <p
              style={{
                color: colors.muted,
                fontSize: 13,
                lineHeight: 1.6,
                marginTop: 20,
              }}
            >
              Local demonstration accounts only.
              No password is required in demo mode.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
