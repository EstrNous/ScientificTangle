import { useMock } from '../api/client.js';

export function isDevRoleSwitcherEnabled() {
  return useMock || import.meta.env.DEV;
}

export function isLiveProductionMode() {
  return !useMock;
}
