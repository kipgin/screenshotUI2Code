import type { AgentEvent } from '@/types';
import { useChatStore } from '@/store/useChatStore';
import { useDiffStore } from '@/store/useDiffStore';
import { useFileStore } from '@/store/useFileStore';
import { useGitStore } from '@/store/useGitStore';

class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(sessionId: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.sessionId = sessionId;
    
    // Construct WS URL based on current origin
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/design/${sessionId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      useChatStore.getState().setConnectionStatus('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const payload: AgentEvent = JSON.parse(event.data);
        this.handleEvent(payload);
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      useChatStore.getState().setConnectionStatus('disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.sessionId) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      setTimeout(() => this.connect(this.sessionId!), delay);
    }
  }

  handleEvent(event: AgentEvent) {
    const chatStore = useChatStore.getState();
    const diffStore = useDiffStore.getState();
    const fileStore = useFileStore.getState();

    switch (event.type) {
      case 'token':
        chatStore.appendToken(event.data);
        break;
      case 'tool_call':
        chatStore.addToolCall(event.data);
        break;
      case 'tool_result':
        chatStore.addToolResult(event.data);
        
        // Intercept diff generation to show in UI
        if (event.data.tool_name === 'generate_diff' || event.data.tool_name === 'preview_diff') {
            diffStore.addPendingDiff({
                path: event.data.data?.path || 'unknown',
                oldContent: event.data.data?.old_content || '',
                newContent: event.data.data?.new_content || '',
                diffText: event.data.data?.diff || '',
                status: 'pending'
            });
        }
        // Refresh file tree if files were created, edited or folders changed
        if (['create_file', 'edit_file', 'create_folder', 'delete_file', 'delete_folder'].includes(event.data.tool_name)) {
             fileStore.refreshFiles(this.sessionId!);
             
             // If the active file in Monaco was edited or created, reload its content!
             const filePath = event.data.data?.path;
             if (filePath && fileStore.activeFilePath === filePath) {
                 fileStore.openFile(this.sessionId!, filePath);
             }
        }
        break;
      case 'done':
        chatStore.finalizeMessage();
        // Since backend does auto-commit after a successful turn, refresh both files and Git logs here
        fileStore.refreshFiles(this.sessionId!);
        useGitStore.getState().refreshGit(this.sessionId!);
        break;
      case 'error':
        chatStore.addMessage({
            id: Date.now().toString(),
            role: 'system',
            content: `Error: ${event.data}`
        });
        break;
      default:
        console.warn('Unknown event type', event);
    }
  }

  sendFeedback(feedback: string) {
    const chatStore = useChatStore.getState();
    if (this.ws?.readyState === WebSocket.OPEN) {
      chatStore.addMessage({
          id: Date.now().toString(),
          role: 'user',
          content: feedback
      });
      // Ensure we create a placeholder for the assistant's streaming reply
      chatStore.prepareAssistantMessage();
      
      this.ws.send(JSON.stringify({ type: 'feedback', content: feedback }));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsClient = new WebSocketClient();
