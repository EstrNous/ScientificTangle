import { describe, expect, it } from 'vitest';
import { validatePasswordChangeForm, validateProfileUpdateForm } from './profileValidation.js';

describe('validateProfileUpdateForm', () => {
  const current = { currentUsername: 'ivan.petrov', currentEmail: 'ivan@example.com' };

  it('accepts username change with password', () => {
    expect(
      validateProfileUpdateForm({
        ...current,
        username: 'new.user',
        email: 'ivan@example.com',
        currentPassword: 'Secret1',
      }),
    ).toBeNull();
  });

  it('rejects when nothing changes', () => {
    expect(
      validateProfileUpdateForm({
        ...current,
        username: 'ivan.petrov',
        email: 'ivan@example.com',
        currentPassword: 'Secret1',
      }),
    ).toBe('profileNoChanges');
  });

  it('requires current password', () => {
    expect(
      validateProfileUpdateForm({
        ...current,
        username: 'new.user',
        email: 'ivan@example.com',
        currentPassword: '',
      }),
    ).toBe('passwordRequired');
  });
});

describe('validatePasswordChangeForm', () => {
  it('accepts valid change', () => {
    expect(
      validatePasswordChangeForm({
        currentPassword: 'OldPassword1',
        newPassword: 'NewPassword1',
        confirmPassword: 'NewPassword1',
      }),
    ).toBeNull();
  });

  it('rejects same password', () => {
    expect(
      validatePasswordChangeForm({
        currentPassword: 'Password1',
        newPassword: 'Password1',
        confirmPassword: 'Password1',
      }),
    ).toBe('passwordSameAsCurrent');
  });
});
