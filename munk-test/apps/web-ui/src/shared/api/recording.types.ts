export interface ClickInteractionPayload {
  kind: 'click'
  clientCommandId: string
  x: number
  y: number
  width: number
  height: number
}

export interface SwipeInteractionPayload {
  kind: 'swipe'
  clientCommandId: string
  startX: number
  startY: number
  endX: number
  endY: number
  width: number
  height: number
  durationMs: number
}

export interface InputInteractionPayload {
  kind: 'input'
  clientCommandId: string
  text: string
  submit?: boolean
}

export interface BackInteractionPayload {
  kind: 'back'
  clientCommandId: string
}

export type InteractionPayload =
  | ClickInteractionPayload
  | SwipeInteractionPayload
  | InputInteractionPayload
  | BackInteractionPayload
