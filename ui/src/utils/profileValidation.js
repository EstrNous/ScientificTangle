import { validatePassword } from './authValidation.js';

const USERNAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$/;

export function validateProfileUpdateForm({ username, email, currentUsername, currentEmail, currentPassword }) {
  if (!currentPassword) {
    return 'passwordRequired';
  }

  const trimmedUsername = username.trim();
  const trimmedEmail = email.trim();
  const usernameChanged = trimmedUsername && trimmedUsername !== currentUsername;
  const emailChanged = trimmedEmail && trimmedEmail !== currentEmail;

  if (!usernameChanged && !emailChanged) {
    return 'profileNoChanges';
  }

  if (usernameChanged && !USERNAME_PATTERN.test(trimmedUsername)) {
    return 'usernameInvalid';
  }

  if (emailChanged && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
    return 'emailInvalid';
  }

  return null;
}

export function validatePasswordChangeForm({ currentPassword, newPassword, confirmPassword }) {
  if (!currentPassword) {
    return 'passwordRequired';
  }

  const passwordError = validatePassword(newPassword);
  if (passwordError) {
    return passwordError;
  }

  if (newPassword !== confirmPassword) {
    return 'passwordMismatch';
  }

  if (newPassword === currentPassword) {
    return 'passwordSameAsCurrent';
  }

  return null;
}
