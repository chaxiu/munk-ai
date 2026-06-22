import winston from 'winston';
const logger = winston.createLogger({
    level: process.env.IOS_BRIDGE_APPIUM_LOG_LEVEL ?? 'info',
    transports: [
        new winston.transports.Console({
            format: winston.format.printf(({ level, message }) => `[appium] ${level}: ${message}`),
        }),
    ],
});
export function createAppiumLogger() {
    return logger;
}
