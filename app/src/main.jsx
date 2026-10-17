import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import { isConfigured } from "./config.js";
import SetupNeeded from "./components/SetupNeeded.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    {isConfigured ? (
      <AuthProvider>
        <App />
      </AuthProvider>
    ) : (
      <SetupNeeded />
    )}
  </StrictMode>,
);
