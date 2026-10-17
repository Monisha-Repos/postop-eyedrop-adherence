import { FLAGS } from "../flags.js";

// Flag shown as symbol + word + color, never color alone.
export default function FlagBadge({ flag }) {
  const info = FLAGS[flag] ?? FLAGS.pending;
  return (
    <span className={`flag-badge flag-${flag}`}>
      <span aria-hidden="true">{info.symbol}</span> {info.label}
    </span>
  );
}
