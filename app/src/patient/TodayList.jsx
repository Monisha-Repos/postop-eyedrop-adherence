import { formatTime } from "../api.js";
import FlagBadge from "../components/FlagBadge.jsx";
import Modal from "../components/Modal.jsx";
import { doseDetail, doseTitle } from "../flags.js";

export default function TodayList({ doses, onClose }) {
  return (
    <Modal title="Today" onClose={onClose}>
      {doses.length === 0 && <p className="muted">No drops scheduled today.</p>}
      <ul className="dose-list large">
        {doses.map((dose) => (
          <li key={dose.id}>
            <span className="dose-time">{formatTime(dose.scheduled_at)}</span>
            <span className="dose-main">
              <strong>{doseTitle(dose)}</strong>
              <span className="muted">{doseDetail(dose)}</span>
            </span>
            <FlagBadge flag={dose.flag} />
          </li>
        ))}
      </ul>
    </Modal>
  );
}
