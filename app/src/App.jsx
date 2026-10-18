
import { useEffect, useMemo, useState } from "react";
import { createApi } from "./api.js";
import { useAuth } from "./auth.jsx";
import Login from "./components/Login.jsx";
import PatientHome from "./patient/PatientHome.jsx";
import ProviderHome from "./provider/ProviderHome.jsx";
import EyeAnalyzer from "./EyeAnalyzer.jsx";

function useStoredFlag(key) {
  const [value, setValue] = useState(() => {
    try {
      return localStorage.getItem(key) === "1";
    } catch {
      return false;
    }
  });

  const update = (next) => {
    setValue(next);

    try {
      localStorage.setItem(key, next ? "1" : "0");
    } catch {
      // Ignore storage errors.
    }
  };

  return [value, update];
}

export default function App() {
  const auth = useAuth();

  const api = useMemo(
    () => createApi(auth.getToken),
    [auth.getToken]
  );

  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);

  const [highContrast, setHighContrast] =
    useStoredFlag("highContrast");
    const [darkMode, setDarkMode] = useStoredFlag("darkMode");

    useEffect(() => {
      document.documentElement.dataset.theme = darkMode
        ? "dark"
        : "light";
    }, [darkMode]);

  const [showEyeAnalyzer, setShowEyeAnalyzer] =
    useState(false);

  useEffect(() => {
    document.documentElement.dataset.contrast =
      highContrast ? "high" : "standard";
  }, [highContrast]);

  useEffect(() => {
    if (!auth.isAuthenticated) {
      setMe(null);
      setShowEyeAnalyzer(false);
      return;
    }

    setError(null);

    api.get("/me")
      .then(setMe)
      .catch((err) => setError(err.message));
  }, [auth.isAuthenticated, api]);

  if (auth.isLoading) {
    return (
      <div className="center-screen">
        Loading…
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return <Login onSignIn={auth.signIn} />;
  }

  if (error) {
    return (
      <Login
        error={error}
        onSignOut={auth.signOut}
      />
    );
  }

  if (!me) {
    return (
      <div className="center-screen">
        Loading…
      </div>
    );
  }

  const settings = {
  highContrast,
  setHighContrast,
  darkMode,
  setDarkMode,
  signOut: auth.signOut
};

  return (
    <>
      {me.role === "patient" ? (
        <PatientHome
          api={api}
          me={me}
          settings={settings}
        />
      ) : (
        <ProviderHome
          api={api}
          me={me}
          signOut={auth.signOut}
        />
      )}

      {me.role === "patient" && (
        <section
          style={{
            maxWidth: 1100,
            margin: "32px auto",
            padding: "0 20px"
          }}
        >
          <div
            style={{
              background: "#F3F8F6",
              border: "1px solid #DCEFE8",
              borderRadius: 24,
              padding: "clamp(20px, 4vw, 40px)",
              color: "#164D49"
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                marginBottom: 24
              }}
            >
              <div
                style={{
                  background: "#DCEFE8",
                  width: 64,
                  height: 64,
                  borderRadius: 18,
                  display: "grid",
                  placeItems: "center",
                  fontSize: 32
                }}
                aria-hidden="true"
              >
                👁️
              </div>

              <div>
                <h2
                  style={{
                    margin: 0,
                    fontSize: 30,
                    color: "#164D49"
                  }}
                >
                  EyeSpy AI
                </h2>

                <p
                  style={{
                    margin: "6px 0 0",
                    color: "#526B68",
                    fontSize: 17
                  }}
                >
                  Your gentle recovery companion
                </p>
              </div>
            </div>

            <div
              style={{
                background: "#FFFFFF",
                padding: 28,
                borderRadius: 20
              }}
            >
              <h3
                style={{
                  fontSize: 27,
                  margin: "0 0 12px",
                  color: "#164D49"
                }}
              >
                Your Eye Recovery Journal
              </h3>

              <p
                style={{
                  color: "#526B68",
                  fontSize: 18,
                  lineHeight: 1.7
                }}
              >
                Save your eye photos, review your
                recovery history, and explore
                AI-generated descriptions of
                visible eye features.
              </p>

              <button
                type="button"
                onClick={() =>
                  setShowEyeAnalyzer((previous) => !previous)
                }
                aria-expanded={showEyeAnalyzer}
                aria-controls="eyespy-journal"
                style={{
                  background: "#176B63",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "16px 28px",
                  borderRadius: 14,
                  fontSize: 18,
                  fontWeight: 700,
                  minHeight: 56,
                  cursor: "pointer",
                  width: "100%",
                  maxWidth: 350
                }}
              >
                {showEyeAnalyzer
                  ? "Close My Eye Journal"
                  : "Open My Eye Journal →"}
              </button>
            </div>

            <div id="eyespy-journal">
              {showEyeAnalyzer && (
                <div
                  style={{
                    background: "#FFFFFF",
                    borderRadius: 20,
                    marginTop: 20,
                    padding: 16
                  }}
                >
                  <EyeAnalyzer api={api} />
                </div>
              )}
            </div>

            <p
              style={{
                color: "#526B68",
                fontSize: 14,
                lineHeight: 1.7,
                marginTop: 20
              }}
            >
              EyeSpy AI is an educational prototype,
              not a medical diagnostic tool.
              Follow your surgeon's postoperative
              instructions.
            </p>
          </div>
        </section>
      )}
    </>
  );
}
