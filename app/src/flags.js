// Every flag has a word and a symbol as well as a color, so meaning never depends on color alone.
export const FLAGS = {
  pending: { label: "Not yet", symbol: "○" },
  on_time: { label: "On time", symbol: "✓" },
  late: { label: "Late", symbol: "◷" },
  early: { label: "Early", symbol: "»" },
  missed: { label: "Missed", symbol: "✕" },
  too_frequent: { label: "Extra lift", symbol: "!" },
};

export const CHART_FLAGS = ["on_time", "late", "early", "missed", "too_frequent"];

export const TAKEN_FLAGS = ["on_time", "late", "early"];

export function doseTitle(dose) {
  return dose.medication ?? "Bottle lifted";
}

export function doseDetail(dose) {
  if (!dose.drops || !dose.eye) return "No drop was due";
  const eye = dose.eye === "both" ? "both eyes" : `${dose.eye} eye`;
  return `${dose.drops} ${dose.drops === 1 ? "drop" : "drops"} · ${eye}`;
}
