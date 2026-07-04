import { describe, expect, it } from 'vitest';
import { validateLoginForm, validatePassword, validateRegisterForm } from './authValidation.js';

describe('validateLoginForm', () => {
  it('accepts non-empty credentials', () => {
    expect(validateLoginForm({ identifier: 'user@example.com', password: 'secret' })).toBeNull();
  });

  it('rejects empty fields', () => {
    expect(validateLoginForm({ identifier: '  ', password: 'secret' })).toBe('identifierRequired');
    expect(validateLoginForm({ identifier: 'user', password: '' })).toBe('passwordRequired');
  });
});

describe('validatePassword', () => {
  it('accepts a valid password', () => {
    expect(validatePassword('Password1')).toBeNull();
  });

  it('rejects passwords without required character classes', () => {
    expect(validatePassword('short1A')).toBe('passwordLength');
    expect(validatePassword('lowercase1')).toBe('passwordUppercase');
    expect(validatePassword('UPPERCASE1')).toBe('passwordLowercase');
    expect(validatePassword('NoDigitsHere')).toBe('passwordDigit');
  });
});

describe('validateRegisterForm', () => {
  const valid = {
    username: 'new.user',
    email: 'user@example.com',
    password: 'Password1',
    confirmPassword: 'Password1',
  };

  it('accepts valid input', () => {
    expect(validateRegisterForm(valid)).toBeNull();
  });

  it('rejects invalid username and mismatched passwords', () => {
    expect(validateRegisterForm({ ...valid, username: 'ab' })).toBe('usernameInvalid');
    expect(validateRegisterForm({ ...valid, confirmPassword: 'Password2' })).toBe('passwordMismatch');
  });
});
