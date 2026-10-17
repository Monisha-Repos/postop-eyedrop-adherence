// Build-time settings from app/.env.local (Vite exposes only VITE_* variables).
const env = import.meta.env;

export const config = {
  auth0Domain: env.VITE_AUTH0_DOMAIN || "",
  auth0ClientId: env.VITE_AUTH0_CLIENT_ID || "",
  auth0Audience: env.VITE_AUTH0_AUDIENCE || "",
  apiBaseUrl: (env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, ""),
  devBypassSub: env.VITE_DEV_BYPASS_SUB || "",
};

export const isConfigured = Boolean(config.devBypassSub || (config.auth0Domain && config.auth0ClientId));

// The provider dashboard's daily buckets are computed in this timezone (see backend/app/schema.py).
export const DASHBOARD_TIMEZONE = "America/New_York";
