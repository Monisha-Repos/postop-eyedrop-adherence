
import { useEffect, useMemo, useState } from "react";
import { createApi } from "./api.js";
import { useAuth } from "./auth.jsx";
import Login from "./components/Login.jsx";
import PatientHome from "./patient/PatientHome.jsx";
import ProviderHome from "./provider/ProviderHome.jsx";
import EyeAnalyzer from "./EyeAnalyzer.jsx";

// Remembered per device; a failed read
// just means the default.
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
      // Ignore storage errors
    }
  };

  return [value, update];
}

// Picks the screen from login state
// and the user's role.
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

  // NEW: Toggle Gemini eye analyzer
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
      .catch((e) => setError(e.message));

  }, [auth.isAuthenticated, api]);

  if (auth.isLoading) {
    return (
      <div className="center-screen" aria-busy="true">
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
      <div className="center-screen" aria-busy="true">
        Loading…
      </div>
    );
  }

  const settings = {
    highContrast,
    setHighContrast,
    signOut: auth.signOut
  };

  return (
    <>
      {/* Existing patient/provider dashboards */}
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

      {/* NEW: Gemini AI Analyzer Section */}
      <div
        style={{
          maxWidth: 700,
          margin: "20px auto",
          padding: 20,
          textAlign: "center"
        }}
      >
        <button
          type="button"
          onClick={() =>
            setShowEyeAnalyzer(!showEyeAnalyzer)
          }
          style={{
            padding: "12px 24px",
            backgroundColor: "#2563eb",
            color: "white",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
            fontSize: 16
          }}
        >
          {showEyeAnalyzer
            ? "Close Eye Analyzer"
            : "Open Gemini Eye Analyzer"}
        </button>

        {showEyeAnalyzer && (
          <EyeAnalyzer api={api} />
        )}
      </div>
    </>
  );
}
