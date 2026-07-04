export function mapApiError(error, fallbackCode = 'request_failed') {
  const code = error?.response?.data?.code ?? error?.code ?? error?.message;
  if (typeof code === 'string' && code.length > 0) {
    return code;
  }
  return fallbackCode;
}

export function createApiError(code, message) {
  const error = new Error(message ?? code);
  error.code = code;
  return error;
}
