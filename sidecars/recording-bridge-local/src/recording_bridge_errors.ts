export class RecordingBridgeSessionError extends Error {
  code: string

  constructor (code: string, message: string) {
    super(message)
    this.name = 'RecordingBridgeSessionError'
    this.code = code
  }
}
