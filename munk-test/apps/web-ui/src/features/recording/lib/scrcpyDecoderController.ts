import type { Ref } from 'vue'

import type {
  BridgeHelloEvent,
  BridgePacketDataEvent,
} from '../types'
import { decodeBase64ToBytes } from './bridgeApi'

import { WebCodecsVideoDecoder } from '@yume-chan/scrcpy-decoder-webcodecs'
import { ScrcpyVideoCodecId } from '@yume-chan/scrcpy'
import type { ScrcpyMediaStreamPacket } from '@yume-chan/scrcpy'
import { BitmapVideoFrameRenderer } from '@yume-chan/scrcpy-decoder-webcodecs/esm/video/render/bitmap.js'

export class ScrcpyDecoderController {
  private hello: BridgeHelloEvent | null = null

  private decoder: WebCodecsVideoDecoder | null = null

  private decoderWriter: WritableStreamDefaultWriter<ScrcpyMediaStreamPacket> | null = null

  constructor(private readonly canvasRef: Ref<HTMLCanvasElement | null>) {}

  getVideoSize(): { width: number, height: number } {
    return {
      width: this.hello?.width ?? this.decoder?.width ?? 0,
      height: this.hello?.height ?? this.decoder?.height ?? 0
    }
  }

  updateHello(event: BridgeHelloEvent): void {
    this.hello = event
  }

  updateSize(width: number, height: number): void {
    if (!this.hello) {
      return
    }

    this.hello = {
      ...this.hello,
      width,
      height
    }
  }

  handleHello(event: BridgeHelloEvent): void {
    this.updateHello(event)
    this.ensureDecoder(event.codec)
  }

  handleConfigurationPacket(dataBase64: string): void {
    if (!this.hello) {
      return
    }

    this.ensureDecoder(this.hello.codec)
    void this.decoderWriter?.write({
      type: 'configuration',
      data: decodeBase64ToBytes(dataBase64)
    })
  }

  handleDataPacket(event: BridgePacketDataEvent): void {
    if (!this.hello) {
      return
    }

    this.ensureDecoder(this.hello.codec)
    void this.decoderWriter?.write({
      type: 'data',
      data: decodeBase64ToBytes(event.dataBase64),
      keyframe: event.keyframe,
      pts: event.pts ? BigInt(event.pts) : undefined
    })
  }

  dispose(): void {
    void this.decoderWriter?.close()
    this.decoderWriter = null
    this.decoder?.dispose()
    this.decoder = null
    this.hello = null
  }

  private ensureDecoder(codec: number): void {
    if (this.decoder && this.decoderWriter) {
      return
    }

    const canvas = this.canvasRef.value
    if (!canvas) {
      throw new Error('canvas not ready')
    }

    if (!WebCodecsVideoDecoder.isSupported) {
      throw new Error('WebCodecs is not supported in this browser')
    }

    this.decoder = new WebCodecsVideoDecoder({
      codec: codec as ScrcpyVideoCodecId,
      renderer: new BitmapVideoFrameRenderer(canvas)
    })
    this.decoderWriter = this.decoder.writable.getWriter()
  }
}
