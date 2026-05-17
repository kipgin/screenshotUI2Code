import React from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { ExplorerPanel } from '@/components/explorer/ExplorerPanel';
import { EditorPanel } from '@/components/editor/EditorPanel';

export default function App() {
  return (
    <div className="w-full h-screen overflow-hidden text-gray-100 font-sans antialiased">
      <AppLayout 
        leftPanel={<ChatPanel />}
        middlePanel={<ExplorerPanel />}
        rightPanel={<EditorPanel />}
      />
    </div>
  );
}
