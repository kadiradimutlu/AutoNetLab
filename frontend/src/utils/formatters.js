export function formatDifficulty(value, t) {
  if (!value) return "-";

  const difficultyKey = value.toLowerCase();

  if (t) {
    return t(difficultyKey);
  }

  return value;
}

export function getDifficultyClass(value) {
  return value || "easy";
}

export function formatStatus(value, t) {
  if (!value) return "-";

  const statusKey = value.toLowerCase();

  if (t) {
    return t(statusKey);
  }

  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatStudentName(studentId) {
  if (!studentId) return "-";

  return studentId.charAt(0).toUpperCase() + studentId.slice(1);
}

export function getCheckStatusLabel(passed) {
  return passed ? "PASS" : "FAIL";
}

export function getCheckStatusClass(passed) {
  return passed ? "pass" : "fail";
}

export function getValidationStatusLabel(validationResult) {
  if (!validationResult) return "-";

  return validationResult.passed ? "PASS" : "FAIL";
}

export function getValidationStatusClass(validationResult) {
  if (!validationResult) return "fail";

  return validationResult.passed ? "pass" : "fail";
}