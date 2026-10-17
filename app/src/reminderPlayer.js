// Plays a reminder: Gemini TTS audio from the backend when available, otherwise the browser's own voice.
//
// iPad Safari only lets a page play sound after a user tap. unlock() must run inside a tap handler;
// after that the same <audio> element can be reused for automatic reminders.

const SILENT_WAV = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";

const audio = new Audio();
let currentUrl = null;

export function unlockAudio() {
  audio.src = SILENT_WAV;
  audio.play().catch(() => {});
  if ("speechSynthesis" in window) {
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(""));
  }
}

export function stopReminder() {
  audio.pause();
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

export async function playReminder(reminder, api) {
  stopReminder();
  if (reminder.has_audio) {
    try {
      const blob = await api.blob(`/patient/reminder/${reminder.reminder_id}/audio`);
      if (currentUrl) URL.revokeObjectURL(currentUrl);
      currentUrl = URL.createObjectURL(blob);
      audio.src = currentUrl;
      await audio.play();
      return;
    } catch {
      // fall through to the on-device voice
    }
  }
  speak(reminder.script);
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.85; // a little slower for older listeners
  window.speechSynthesis.speak(utterance);
}
