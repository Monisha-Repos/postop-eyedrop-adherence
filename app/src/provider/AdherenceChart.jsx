import { parseDate } from "../api.js";
import { DASHBOARD_TIMEZONE } from "../config.js";
import { CHART_FLAGS, FLAGS } from "../flags.js";

// Stacked bar per day, drawn with plain HTML/CSS (no chart library).
export default function AdherenceChart({ days }) {
  if (days.length === 0) return <p className="muted">No data yet.</p>;

  const totals = days.map((d) => CHART_FLAGS.reduce((sum, f) => sum + d[f], 0));
  const max = Math.max(1, ...totals);

  return (
    <figure className="chart">
      <div className="chart-bars" role="img" aria-label="Doses per day by result">
        {days.map((d, i) => {
          const label = parseDate(d.day).toLocaleDateString([], {
            month: "short",
            day: "numeric",
            timeZone: DASHBOARD_TIMEZONE,
          });
          const summary = CHART_FLAGS.filter((f) => d[f] > 0)
            .map((f) => `${d[f]} ${FLAGS[f].label.toLowerCase()}`)
            .join(", ");
          return (
            <div className="chart-column" key={d.day} title={`${label}: ${summary || "no doses"}`}>
              <div className="chart-stack" style={{ height: `${(100 * totals[i]) / max}%` }}>
                {CHART_FLAGS.filter((f) => d[f] > 0).map((f) => (
                  <div key={f} className={`chart-segment bg-${f}`} style={{ flexGrow: d[f] }} />
                ))}
              </div>
              <span className="chart-label">{label}</span>
            </div>
          );
        })}
      </div>
      <figcaption className="chart-legend">
        {CHART_FLAGS.map((f) => (
          <span key={f}>
            <span className={`legend-swatch bg-${f}`} aria-hidden="true" /> {FLAGS[f].symbol} {FLAGS[f].label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
