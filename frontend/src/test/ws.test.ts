import { describe, it, expect, vi, beforeEach } from 'vitest';
import { wsClient } from '@/api/ws';
import { useChatStore } from '@/store/useChatStore';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  onopen: () => void = () => {};
  onmessage: (event: any) => void = () => {};
  onclose: () => void = () => {};
  onerror: (err: any) => void = () => {};
  send = vi.fn();
  close = vi.fn();
  readyState = 0; // CONNECTING
}

globalThis.WebSocket = MockWebSocket as any;
(globalThis as any).WebSocket = MockWebSocket as any;

describe('WebSocket Client Tests', () => {
  beforeEach(() => {
    useChatStore.setState({ sessionId: null, messages: [], connectionStatus: 'disconnected' });
    wsClient.disconnect();
  });

  it('connects and updates store status', () => {
    wsClient.connect('session-123');
    
    // Simulate connection open
    const wsInstance = (wsClient as any).ws;
    expect(wsInstance).not.toBeNull();
    
    wsInstance.readyState = MockWebSocket.OPEN;
    wsInstance.onopen();
    expect(useChatStore.getState().connectionStatus).toBe('connected');
  });

  it('handles token events', () => {
    useChatStore.getState().addMessage({ id: '1', role: 'user', content: 'hello' });
    useChatStore.getState().prepareAssistantMessage();

    wsClient.connect('session-123');
    const wsInstance = (wsClient as any).ws;
    
    wsInstance.onmessage({ data: JSON.stringify({ type: 'token', data: 'Hello' }) });
    
    const messages = useChatStore.getState().messages;
    expect(messages[messages.length - 1].content).toBe('Hello');
  });

  it('sends feedback', () => {
    wsClient.connect('session-123');
    const wsInstance = (wsClient as any).ws;
    
    wsInstance.readyState = MockWebSocket.OPEN;
    wsInstance.onopen();

    wsClient.sendFeedback('Make it red');
    expect(wsInstance.send).toHaveBeenCalledWith(JSON.stringify({ type: 'feedback', content: 'Make it red' }));
  });
});
