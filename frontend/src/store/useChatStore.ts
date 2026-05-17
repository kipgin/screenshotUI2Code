import { create } from 'zustand';
import { ChatMessage, ToolCall, ToolResult } from '@/types';
import { v4 as uuidv4 } from 'uuid';

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  connectionStatus: 'disconnected' | 'connecting' | 'connected';
  
  setSessionId: (id: string) => void;
  setConnectionStatus: (status: 'disconnected' | 'connecting' | 'connected') => void;
  
  addMessage: (msg: ChatMessage) => void;
  prepareAssistantMessage: () => void;
  appendToken: (token: string) => void;
  addToolCall: (call: ToolCall) => void;
  addToolResult: (result: ToolResult) => void;
  finalizeMessage: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessionId: null,
  messages: [],
  connectionStatus: 'disconnected',

  setSessionId: (id) => set({ sessionId: id }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  prepareAssistantMessage: () => set((state) => {
    // Only prepare if the last message isn't already a streaming assistant message
    const lastMsg = state.messages[state.messages.length - 1];
    if (lastMsg?.role === 'assistant' && lastMsg?.isStreaming) return state;

    return {
      messages: [
        ...state.messages,
        {
          id: uuidv4(),
          role: 'assistant',
          content: '',
          isStreaming: true,
          toolCalls: [],
          toolResults: [],
        }
      ]
    };
  }),

  appendToken: (token) => set((state) => {
    const msgs = [...state.messages];
    const lastMsg = msgs[msgs.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
      lastMsg.content += token;
    }
    return { messages: msgs };
  }),

  addToolCall: (call) => set((state) => {
    const msgs = [...state.messages];
    const lastMsg = msgs[msgs.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
      lastMsg.toolCalls = lastMsg.toolCalls || [];
      lastMsg.toolCalls.push(call);
    }
    return { messages: msgs };
  }),

  addToolResult: (result) => set((state) => {
    const msgs = [...state.messages];
    const lastMsg = msgs[msgs.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
      lastMsg.toolResults = lastMsg.toolResults || [];
      lastMsg.toolResults.push(result);
    }
    return { messages: msgs };
  }),

  finalizeMessage: () => set((state) => {
    const msgs = [...state.messages];
    const lastMsg = msgs[msgs.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.isStreaming = false;
    }
    return { messages: msgs };
  }),
}));
