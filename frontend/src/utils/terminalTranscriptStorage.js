const TRANSCRIPT_STORAGE_PREFIX = "autonetlab_terminal_transcript_v1";
const DEFAULT_STUDENT_ID = "student";
const DEFAULT_UNKNOWN_VALUE = "unknown";

export const TERMINAL_TRANSCRIPT_MAX_LINES = 1500;
export const TERMINAL_TRANSCRIPT_MAX_CHARS = 200000;
export const TERMINAL_TRANSCRIPT_TTL_MS = 7 * 24 * 60 * 60 * 1000;

function canUseLocalStorage() {
  try {
    return typeof window !== "undefined" && Boolean(window.localStorage);
  } catch {
    return false;
  }
}

function normalizeStorageSegment(value, fallback = DEFAULT_UNKNOWN_VALUE) {
  const normalizedValue = String(value || "").trim() || fallback;
  return encodeURIComponent(normalizedValue);
}

function normalizeLine(line) {
  const safeLine = line && typeof line === "object" ? line : {};
  const safeKind = ["system", "output", "command", "error"].includes(safeLine.kind)
    ? safeLine.kind
    : "output";

  return {
    kind: safeKind,
    text: String(safeLine.text ?? ""),
    timestamp: safeLine.timestamp || new Date().toISOString()
  };
}

function estimateTranscriptSize(lines) {
  return lines.reduce((total, line) => {
    return total + String(line.text || "").length + String(line.kind || "").length + 32;
  }, 0);
}

function getTranscriptKeys() {
  if (!canUseLocalStorage()) {
    return [];
  }

  const keys = [];

  for (let index = 0; index < window.localStorage.length; index += 1) {
    const key = window.localStorage.key(index);

    if (key && key.startsWith(TRANSCRIPT_STORAGE_PREFIX)) {
      keys.push(key);
    }
  }

  return keys;
}

function readTranscriptPayload(key) {
  if (!canUseLocalStorage() || !key) {
    return null;
  }

  try {
    const rawPayload = window.localStorage.getItem(key);

    if (!rawPayload) {
      return null;
    }

    return JSON.parse(rawPayload);
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function isExpiredPayload(payload, now = Date.now()) {
  if (!payload?.updatedAt) {
    return true;
  }

  const updatedAtMs = new Date(payload.updatedAt).getTime();

  if (Number.isNaN(updatedAtMs)) {
    return true;
  }

  return now - updatedAtMs > TERMINAL_TRANSCRIPT_TTL_MS;
}

export function getTerminalTranscriptStorageKey({
  studentId = DEFAULT_STUDENT_ID,
  sessionId,
  deviceId
}) {
  if (!sessionId || !deviceId) {
    return "";
  }

  return [
    TRANSCRIPT_STORAGE_PREFIX,
    normalizeStorageSegment(studentId, DEFAULT_STUDENT_ID),
    normalizeStorageSegment(sessionId),
    normalizeStorageSegment(deviceId)
  ].join("_");
}

export function trimTerminalTranscriptLines(lines = []) {
  const normalizedLines = Array.isArray(lines)
    ? lines.map(normalizeLine)
    : [];

  let trimmedLines = normalizedLines.slice(-TERMINAL_TRANSCRIPT_MAX_LINES);

  while (
    trimmedLines.length > 1 &&
    estimateTranscriptSize(trimmedLines) > TERMINAL_TRANSCRIPT_MAX_CHARS
  ) {
    trimmedLines = trimmedLines.slice(1);
  }

  return trimmedLines;
}

export function cleanupExpiredTerminalTranscripts() {
  if (!canUseLocalStorage()) {
    return;
  }

  const now = Date.now();

  getTranscriptKeys().forEach((key) => {
    const payload = readTranscriptPayload(key);

    if (!payload || isExpiredPayload(payload, now)) {
      window.localStorage.removeItem(key);
    }
  });
}

export function readTerminalTranscript({
  studentId = DEFAULT_STUDENT_ID,
  sessionId,
  deviceId
}) {
  if (!canUseLocalStorage()) {
    return [];
  }

  const key = getTerminalTranscriptStorageKey({
    studentId,
    sessionId,
    deviceId
  });

  if (!key) {
    return [];
  }

  const payload = readTranscriptPayload(key);

  if (!payload) {
    return [];
  }

  if (isExpiredPayload(payload)) {
    window.localStorage.removeItem(key);
    return [];
  }

  if (Array.isArray(payload.lines)) {
    return trimTerminalTranscriptLines(payload.lines);
  }

  if (typeof payload.transcript === "string") {
    return trimTerminalTranscriptLines(
      payload.transcript.split("\n").map((text) => ({
        kind: "output",
        text
      }))
    );
  }

  return [];
}

export function writeTerminalTranscript({
  studentId = DEFAULT_STUDENT_ID,
  sessionId,
  deviceId,
  lines = []
}) {
  if (!canUseLocalStorage()) {
    return;
  }

  const key = getTerminalTranscriptStorageKey({
    studentId,
    sessionId,
    deviceId
  });

  if (!key) {
    return;
  }

  const trimmedLines = trimTerminalTranscriptLines(lines);
  const payload = {
    version: 1,
    studentId: studentId || DEFAULT_STUDENT_ID,
    sessionId,
    deviceId,
    updatedAt: new Date().toISOString(),
    limits: {
      maxLines: TERMINAL_TRANSCRIPT_MAX_LINES,
      maxChars: TERMINAL_TRANSCRIPT_MAX_CHARS
    },
    lines: trimmedLines
  };

  try {
    window.localStorage.setItem(key, JSON.stringify(payload));
  } catch (error) {
    const compactLines = trimTerminalTranscriptLines(
      trimmedLines.slice(-Math.max(100, Math.floor(TERMINAL_TRANSCRIPT_MAX_LINES / 2)))
    );

    try {
      window.localStorage.setItem(
        key,
        JSON.stringify({
          ...payload,
          lines: compactLines
        })
      );
    } catch (secondError) {
      console.warn("Terminal transcript could not be stored locally.", secondError || error);
    }
  }
}

export function removeTerminalTranscript({
  studentId = DEFAULT_STUDENT_ID,
  sessionId,
  deviceId
}) {
  if (!canUseLocalStorage()) {
    return;
  }

  const key = getTerminalTranscriptStorageKey({
    studentId,
    sessionId,
    deviceId
  });

  if (key) {
    window.localStorage.removeItem(key);
  }
}

export function clearTerminalTranscriptsForSession(sessionId) {
  if (!canUseLocalStorage() || !sessionId) {
    return;
  }

  const encodedSessionId = normalizeStorageSegment(sessionId);

  getTranscriptKeys().forEach((key) => {
    const payload = readTranscriptPayload(key);

    if (payload?.sessionId === sessionId || key.includes(`_${encodedSessionId}_`)) {
      window.localStorage.removeItem(key);
    }
  });
}
