export function mapApiError(error, fallbackCode = 'request_failed') {
  const status = error?.response?.status;
  if (status === 403) {
    return 'forbidden';
  }
  if (status === 404) {
    return 'not_found';
  }
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
