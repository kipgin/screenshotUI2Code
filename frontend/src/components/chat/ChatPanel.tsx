import React, { useRef, useState, useEffect } from 'react';
import { useChatStore } from '@/store/useChatStore';
import { uploadScreenshot } from '@/api/rest';
import { wsClient } from '@/api/ws';
import { Send, Upload, ImageIcon, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function formatMessageContent(content: string): string {
  if (!content) return '';
  
  // Match the entire ```tool_call block (and support incomplete streaming blocks)
  const toolCallRegex = /```tool_call\s*\n([\s\S]*?)(?:\n```|$)/g;
  
  return content.replace(toolCallRegex, (match, jsonStr) => {
    try {
      // Try to parse full JSON first
      const parsed = JSON.parse(jsonStr.trim());
      if (parsed.name === 'create_file' && parsed.arguments) {
        const path = parsed.arguments.path || 'file';
        const fileContent = parsed.arguments.content || '';
        const ext = path.split('.').pop() || 'html';
        return `\n\n**Created File:** \`${path}\`\n\`\`\`${ext}\n${fileContent}\n\`\`\`\n`;
      }
      return ''; // Hide other tool calls from chat bubbles
    } catch (e) {
      // If JSON is incomplete (streaming), extract arguments using robust regex / string slicing
      const pathMatch = jsonStr.match(/"path"\s*:\s*"([^"]*)"/);
      const path = pathMatch ? pathMatch[1] : '';
      
      const contentStart = jsonStr.indexOf('"content"');
      if (contentStart !== -1) {
        const contentValueStart = jsonStr.indexOf('"', contentStart + 9);
        if (contentValueStart !== -1) {
          const rest = jsonStr.substring(contentValueStart + 1);
          // Clean up JSON escaping on the fly for beautiful streaming
          const unescaped = rest
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, '\\')
            .replace(/"\s*\}\s*\}?$/, ''); // remove trailing JSON braces
          
          const ext = path.split('.').pop() || 'html';
          return `\n\n**Writing File:** \`${path || '...'}\`\n\`\`\`${ext}\n${unescaped}\n\`\`\`\n`;
        }
      }
      return '\n\n*(Calling Tool...)*\n';
    }
  });
}

export function ChatPanel() {
  const { messages, connectionStatus, setSessionId } = useChatStore();
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check if the user is already scrolled to the bottom (within a 100px threshold)
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= 100;

    // If streaming, scroll instantly; otherwise, use smooth scrolling
    const lastMsg = messages[messages.length - 1];
    const isStreaming = lastMsg?.role === 'assistant' && lastMsg?.isStreaming;

    if (isAtBottom) {
      if (isStreaming) {
        container.scrollTop = container.scrollHeight;
      } else {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [messages]);

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    try {
      const res = await uploadScreenshot(file, 'html/css', false);
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      const chatStore = useChatStore.getState();
      let sessionId = '';
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done && !buffer) break;
        
        const chunk = value ? decoder.decode(value, { stream: true }) : '';
        buffer += chunk;
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.substring(6));
              if (data.type === 'session_id') {
                sessionId = data.data;
                setSessionId(sessionId);
                wsClient.connect(sessionId);
                chatStore.prepareAssistantMessage();
              } else {
                wsClient.handleEvent(data);
              }
            } catch (jsonErr) {
              console.error('Failed to parse SSE JSON line:', trimmed, jsonErr);
            }
          }
        }
        
        if (done) break;
      }
    } catch (err) {
      console.error('Upload stream error:', err);
    } finally {
      setIsUploading(false);
      setFile(null);
    }
  };

  const handleSend = () => {
    if (!input.trim() || connectionStatus !== 'connected') return;
    wsClient.sendFeedback(input);
    setInput('');
  };

  return (
    <div className="flex flex-col h-full relative">
      <div className="p-4 border-b border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] flex items-center justify-between">
        <h2 className="font-semibold text-[15px] flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connectionStatus === 'connected' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          Agent Chat
        </h2>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-[rgba(255,255,255,0.05)] flex items-center justify-center">
              <ImageIcon size={32} className="opacity-50" />
            </div>
            <div>
              <p className="font-medium text-gray-300">No active session</p>
              <p className="text-sm mt-1">Upload a screenshot to begin</p>
            </div>
            
            <input 
              type="file" 
              accept="image/*" 
              className="hidden" 
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            
            {!file ? (
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="btn-primary mt-2"
              >
                <Upload size={16} /> Select Image
              </button>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <p className="text-sm text-emerald-400">{file.name}</p>
                <button 
                  onClick={handleUpload}
                  disabled={isUploading}
                  className="btn-primary"
                >
                  {isUploading ? <Loader2 size={16} className="animate-spin" /> : 'Start Generation'}
                </button>
              </div>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-[14px] leading-relaxed shadow-sm
              ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-sm' : 'bg-[rgba(255,255,255,0.06)] text-gray-200 rounded-bl-sm border border-[rgba(255,255,255,0.05)]'}`}>
              <div className="prose prose-invert max-w-none text-[14px] leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 prose-p:my-1 prose-ul:my-1 prose-ol:my-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {formatMessageContent(msg.content || (msg.isStreaming ? '...' : ''))}
                </ReactMarkdown>
              </div>
              
              {/* Tool Calls Display */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mt-3 space-y-2 border-t border-[rgba(255,255,255,0.1)] pt-2">
                  {msg.toolCalls.map((tc, idx) => (
                    <div key={idx} className="text-xs font-mono bg-black/30 rounded p-2 text-indigo-300">
                      🛠 {tc.name}(...)
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-[rgba(255,255,255,0.08)] bg-[rgba(0,0,0,0.2)]">
        <div className="flex items-center gap-2">
          {(() => {
            const lastMsg = messages[messages.length - 1];
            const isStreaming = lastMsg?.role === 'assistant' && lastMsg?.isStreaming;
            return (
              <>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !isStreaming && handleSend()}
                  placeholder={isStreaming ? "Agent is thinking..." : "Give feedback..."}
                  className="flex-1 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={connectionStatus !== 'connected' || isStreaming}
                />
                <button 
                  onClick={handleSend}
                  disabled={!input.trim() || connectionStatus !== 'connected' || isStreaming}
                  className="p-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-white flex items-center justify-center shadow-lg"
                >
                  <Send size={18} />
                </button>
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
