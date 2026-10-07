export class IOSDeviceBridgeError extends Error {
  statusCode: number;
  code: string;
  details: Record<string, unknown> | undefined;

  constructor(
    code: string,
    message: string,
    statusCode = 500,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'IOSDeviceBridgeError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}
