export const DELIVERY_CHANNELS = [
  'chat',
  'desktop',
  'mobile_push',
  'webhook',
  'slack',
  'inbox',
] as const;
export type DeliveryChannel = (typeof DELIVERY_CHANNELS)[number];

export const DELIVERY_RECEIPT_RESULTS = ['succeeded', 'failed', 'muted'] as const;
export type DeliveryReceiptResult = (typeof DELIVERY_RECEIPT_RESULTS)[number];

export interface DeliveryReceipt {
  receipt_id: string;
  signal_id: string;
  event_id: string;
  channel: DeliveryChannel | string;
  attempted_at: string;
  result: DeliveryReceiptResult | string;
  error: string;
  policy_reason: string;
}

export interface DeliveryReceiptSnapshot {
  items: DeliveryReceipt[];
  count: number;
  next_cursor: string;
  updated_at: string;
}
