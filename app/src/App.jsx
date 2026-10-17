import { useEffect, useMemo, useState } from "react";
import { createApi } from "./api.js";
import { useAuth } from "./auth.jsx";
import Login from "./components/Login.jsx";
import PatientHome from "./patient/PatientHome.jsx";
import ProviderHome from "./provider/ProviderHome.jsx";

// Remembered per device; a failed read (private mode, blocked storage) just means the default.
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
      // ignore
    }
  };
  return [value, update];
}

// Picks the screen from login state and the user's role (from the backend's /me).
export default function App() {
  const auth = useAuth();
  const api = useMemo(() => createApi(auth.getToken), [auth.getToken]);
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [highContrast, setHighContrast] = useStoredFlag("highContrast");

  useEffect(() => {
    document.documentElement.dataset.contrast = highContrast ? "high" : "standard";
  }, [highContrast]);

  useEffect(() => {
    if (!auth.isAuthenticated) {
      setMe(null);
      return;
    }
    setError(null);
    api.get("/me").then(setMe).catch((e) => setError(e.message));
  }, [auth.isAuthenticated, api]);

  if (auth.isLoading) return <div className="center-screen" aria-busy="true">Loading…</div>;
  if (!auth.isAuthenticated) return <Login onSignIn={auth.signIn} />;
  if (error) return <Login error={error} onSignOut={auth.signOut} />;
  if (!me) return <div className="center-screen" aria-busy="true">Loading…</div>;

  const settings = { highContrast, setHighContrast, signOut: auth.signOut };
  return me.role === "patient" ? (
    <PatientHome api={api} me={me} settings={settings} />
  ) : (
    <ProviderHome api={api} me={me} signOut={auth.signOut} />
  );
}
