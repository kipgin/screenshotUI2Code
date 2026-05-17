import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AppLayout } from '@/components/layout/AppLayout';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { ExplorerPanel } from '@/components/explorer/ExplorerPanel';
import { EditorPanel } from '@/components/editor/EditorPanel';
import App from '@/App';

// Mock canvas and resize observer which might be needed by some components (Monaco)
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock Monaco Editor
vi.mock('@monaco-editor/react', () => ({
  default: () => <div data-testid="monaco-editor" />,
  DiffEditor: () => <div data-testid="monaco-diff-editor" />
}));

// Mock the WS client
vi.mock('@/api/ws', () => ({
  wsClient: {
    connect: vi.fn(),
    sendFeedback: vi.fn(),
    disconnect: vi.fn()
  }
}));

describe('Component Module Tests', () => {
  it('AppLayout renders all panels', () => {
    render(
      <AppLayout 
        leftPanel={<div data-testid="left-panel" />}
        middlePanel={<div data-testid="middle-panel" />}
        rightPanel={<div data-testid="right-panel" />}
      />
    );
    
    expect(screen.getByTestId('left-panel')).toBeInTheDocument();
    expect(screen.getByTestId('middle-panel')).toBeInTheDocument();
    expect(screen.getByTestId('right-panel')).toBeInTheDocument();
  });

  it('ChatPanel renders empty state initially', () => {
    render(<ChatPanel />);
    expect(screen.getByText('Agent Chat')).toBeInTheDocument();
    expect(screen.getByText('No active session')).toBeInTheDocument();
    expect(screen.getByText('Select Image')).toBeInTheDocument();
  });

  it('ExplorerPanel renders tabs', () => {
    render(<ExplorerPanel />);
    expect(screen.getByText('Files')).toBeInTheDocument();
    expect(screen.getByText('Git')).toBeInTheDocument();
    expect(screen.getByText('No files in workspace')).toBeInTheDocument();
  });

  it('EditorPanel renders tabs and code by default', () => {
    render(<EditorPanel />);
    expect(screen.getByText('Code')).toBeInTheDocument();
    expect(screen.getByText('Diffs')).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();
    expect(screen.getByText('Select a file to view code')).toBeInTheDocument();
  });

  it('App renders without crashing', () => {
    render(<App />);
    expect(screen.getByText('Agent Chat')).toBeInTheDocument();
    expect(screen.getByText('Files')).toBeInTheDocument();
    expect(screen.getByText('Code')).toBeInTheDocument();
  });
});
