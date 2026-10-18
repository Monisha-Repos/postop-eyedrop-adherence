
/*
 * EyeSpy AI Reminder Player
 *
 * Features:
 * - Gemini audio fallback
 * - Browser voice selection
 * - Speaking speed
 * - Play, pause, resume, stop
 * - Snooze reminders
 *
 * Snooze only delays the spoken reminder.
 * It does not change medication schedules.
 */

const SILENT_WAV =
  "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";

const audio = new Audio();

let currentUrl = null;
let currentReminder = null;
let currentApi = null;
let playbackGeneration = 0;
let snoozeTimer = null;

const SETTINGS_KEY = "eyespy_voice_settings";

const defaultSettings = {
  voiceURI: "",
  rate: 0.85,
  preferBrowserVoice: false
};

export function getVoiceSettings() {
  try {
    const saved = JSON.parse(
      localStorage.getItem(SETTINGS_KEY) || "{}"
    );

    return {
      ...defaultSettings,
      ...saved
    };
  } catch {
    return { ...defaultSettings };
  }
}

export function saveVoiceSettings(settings) {
  const updated = {
    ...getVoiceSettings(),
    ...settings
  };

  localStorage.setItem(
    SETTINGS_KEY,
    JSON.stringify(updated)
  );

  return updated;
}

export function getAvailableVoices() {
  if (!("speechSynthesis" in window)) {
    return [];
  }

  return window.speechSynthesis.getVoices();
}

export function unlockAudio() {
  audio.src = SILENT_WAV;
  audio.play().catch(() => {});

  if ("speechSynthesis" in window) {
    window.speechSynthesis.speak(
      new SpeechSynthesisUtterance("")
    );
  }
}

function clearSnooze() {
  if (snoozeTimer !== null) {
    clearTimeout(snoozeTimer);
    snoozeTimer = null;
  }
}

function stopPlaybackOnly() {
  playbackGeneration += 1;

  audio.pause();

  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

export function stopReminder() {
  clearSnooze();
  stopPlaybackOnly();
}

export function pauseReminder() {
  if (!audio.paused) {
    audio.pause();
  }

  if ("speechSynthesis" in window) {
    window.speechSynthesis.pause();
  }
}

export function resumeReminder() {
  if (!audio.paused && !audio.ended) {
    return;
  }

  if (
    audio.src &&
    audio.src !== SILENT_WAV &&
    audio.currentTime > 0 &&
    !audio.ended
  ) {
    audio.play().catch(() => {});
    return;
  }

  if (
    "speechSynthesis" in window &&
    window.speechSynthesis.paused
  ) {
    window.speechSynthesis.resume();
  }
}

export function getPlaybackState() {
  const speaking =
    "speechSynthesis" in window &&
    window.speechSynthesis.speaking;

  const pausedSpeech =
    "speechSynthesis" in window &&
    window.speechSynthesis.paused;

  return {
    playing:
      (!audio.paused && !audio.ended) ||
      (speaking && !pausedSpeech),

    paused:
      (speaking && pausedSpeech) ||
      (audio.paused &&
        audio.currentTime > 0 &&
        !audio.ended)
  };
}

function speak(text) {
  if (!("speechSynthesis" in window)) {
    return;
  }

  const settings = getVoiceSettings();

  const utterance = new SpeechSynthesisUtterance(
    text || "It's time for your eye drops."
  );

  utterance.rate = settings.rate;

  const voices = getAvailableVoices();

  const selectedVoice = voices.find(
    (voice) => voice.voiceURI === settings.voiceURI
  );

  if (selectedVoice) {
    utterance.voice = selectedVoice;
    utterance.lang = selectedVoice.lang;
  }

  window.speechSynthesis.speak(utterance);
}

export async function playReminder(reminder, api) {
  clearSnooze();
  stopPlaybackOnly();

  currentReminder = reminder;
  currentApi = api;

  const generation = playbackGeneration;
  const settings = getVoiceSettings();

  if (
    reminder?.has_audio &&
    !settings.preferBrowserVoice
  ) {
    try {
      const blob = await api.blob(
        `/patient/reminder/${reminder.reminder_id}/audio`
      );

      if (generation !== playbackGeneration) {
        return;
      }

      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
      }

      currentUrl = URL.createObjectURL(blob);
      audio.src = currentUrl;
      audio.currentTime = 0;

      await audio.play();
      return;
    } catch {
      if (generation !== playbackGeneration) {
        return;
      }

      // Use the device voice if Gemini is unavailable.
    }
  }

  if (generation !== playbackGeneration) {
    return;
  }

  speak(reminder?.script);
}

export function snoozeReminder(minutes = 5) {
  if (!currentReminder) {
    return false;
  }

  const reminder = currentReminder;
  const api = currentApi;

  clearSnooze();
  stopPlaybackOnly();

  snoozeTimer = setTimeout(() => {
    snoozeTimer = null;
    playReminder(reminder, api);
  }, minutes * 60 * 1000);

  return true;
}

export function cancelSnooze() {
  clearSnooze();
}

export function getCurrentReminder() {
  return currentReminder;
}
