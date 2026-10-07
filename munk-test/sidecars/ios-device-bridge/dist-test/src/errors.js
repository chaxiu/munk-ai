export class IOSDeviceBridgeError extends Error {
    statusCode;
    code;
    details;
    constructor(code, message, statusCode = 500, details) {
        super(message);
        this.name = 'IOSDeviceBridgeError';
        this.code = code;
        this.statusCode = statusCode;
        this.details = details;
    }
}
