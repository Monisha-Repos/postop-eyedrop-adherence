import { useState } from "react";
import Modal from "../components/Modal.jsx";

const HUMOR_OPTIONS = [
  { value: "full", label: "Full humor" },
  { value: "mild", label: "A little humor" },
  { value: "off", label: "No jokes" },
];

export default function PatientSettings({ api, humor, onHumorChange, settings, onClose }) {
  const [error, setError] = useState(null);

  const chooseHumor = async (value) => {
    const previous = humor;
    onHumorChange(value);
    try {
      await api.patch("/patient/settings", { humor_level: value });
      setError(null);
    } catch {
      onHumorChange(previous);
      setError("Couldn't save the setting.");
    }
  };

  return (
    <Modal title="Settings" onClose={onClose}>
      <fieldset className="setting-group">
        <legend>Reminder voice</legend>
        {HUMOR_OPTIONS.map((option) => (
          <label key={option.value} className="choice">
            <input
              type="radio"
              name="humor"
              value={option.value}
              checked={humor === option.value}
              onChange={() => chooseHumor(option.value)}
            />
            {option.label}
          </label>
        ))}
      </fieldset>

      <fieldset className="setting-group">
        <legend>Screen</legend>
        <label className="choice">
          <input
            type="checkbox"
            checked={settings.highContrast}
            onChange={(e) => settings.setHighContrast(e.target.checked)}
          />
          High contrast
        </label>
      </fieldset>

      {error && <p className="error" role="alert">{error}</p>}

      <button className="big-button danger" onClick={settings.signOut}>Sign out</button>
    </Modal>
  );
}
