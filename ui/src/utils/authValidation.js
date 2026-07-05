const USERNAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$/;

export function validateLoginForm({ identifier, password }) {
  if (!identifier.trim()) {
    return 'identifierRequired';
  }
  if (!password) {
    return 'passwordRequired';
  }
  return null;
}

export function validatePassword(password) {
  if (password.length < 8 || password.length > 128) {
    return 'passwordLength';
  }
  if (!/[A-Z]/.test(password)) {
    return 'passwordUppercase';
  }
  if (!/[a-z]/.test(password)) {
    return 'passwordLowercase';
  }
  if (!/[0-9]/.test(password)) {
    return 'passwordDigit';
  }
  return null;
}

export function validateRegisterForm({ username, email, password, confirmPassword }) {
  const trimmedUsername = username.trim();
  const trimmedEmail = email.trim();

  if (!trimmedUsername || !USERNAME_PATTERN.test(trimmedUsername)) {
    return 'usernameInvalid';
  }
  if (!trimmedEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
    return 'emailInvalid';
  }
  const passwordError = validatePassword(password);
  if (passwordError) {
    return passwordError;
  }
  if (password !== confirmPassword) {
    return 'passwordMismatch';
  }
  return null;
}
