
import { config } from "./config.js";

// Thin fetch wrapper.
// Every request carries the user's bearer token.
export function createApi(getToken) {

  async function send(path, { method = "GET", body } = {}) {

    const headers = {
      Authorization: `Bearer ${await getToken()}`
    };

    // Support both JSON and image uploads
    const isFormData = body instanceof FormData;

    if (body !== undefined && !isFormData) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(config.apiBaseUrl + path, {
      method,
      headers,
      body:
        body === undefined
          ? undefined
          : isFormData
            ? body
            : JSON.stringify(body),
    });

    if (!res.ok) {
      let detail = res.statusText;

      try {
        const data = await res.json();

        if (typeof data.detail === "string") {
          detail = data.detail;
        }
      } catch {
        // Not JSON; keep the status text
      }

      const error = new Error(
        `Server error ${res.status}: ${detail}`
      );

      error.status = res.status;
      throw error;
    }

    return res;
  }

  return {
    get: async (path) =>
      (await send(path)).json(),

    patch: async (path, body) =>
      (await send(path, {
        method: "PATCH",
        body
      })).json(),

    // NEW: Support POST requests and image uploads
    post: async (path, body) =>
      (await send(path, {
        method: "POST",
        body
      })).json(),

    blob: async (path) =>
      (await send(path)).blob(),
  };
}

// Postgres timestamps can carry microseconds;
// trim the fraction so every browser parses them.
export function parseDate(iso) {
  return iso
    ? new Date(iso.replace(/\.\d+/, ""))
    : null;
}

export function formatTime(iso) {
  return (
    parseDate(iso)?.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit"
    }) ?? ""
  );
}
