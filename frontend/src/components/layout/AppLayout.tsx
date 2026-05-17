import React, { ReactNode, useState, useRef, useEffect } from 'react';

interface AppLayoutProps {
  leftPanel: ReactNode;
  middlePanel: ReactNode;
  rightPanel: ReactNode;
}

export function AppLayout({ leftPanel, middlePanel, rightPanel }: AppLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(380);
  const [middleWidth, setMiddleWidth] = useState(280);
  
  const isResizingLeft = useRef(false);
  const isResizingMiddle = useRef(false);
  
  const startResizeLeft = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingLeft.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };
  
  const startResizeMiddle = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingMiddle.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingLeft.current) {
        const newWidth = Math.max(300, Math.min(600, e.clientX));
        setLeftWidth(newWidth);
      } else if (isResizingMiddle.current) {
        const newWidth = Math.max(200, Math.min(500, e.clientX - leftWidth));
        setMiddleWidth(newWidth);
      }
    };
    
    const handleMouseUp = () => {
      isResizingLeft.current = false;
      isResizingMiddle.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [leftWidth]);
  
  return (
    <div className="flex h-screen w-full bg-[#0f1115] text-[#f0f2f5] overflow-hidden">
      {/* Left Panel: Chat & Upload */}
      <div 
        className="bg-[#161920] flex flex-col z-10 shadow-[4px_0_24px_rgba(0,0,0,0.2)]"
        style={{ width: `${leftWidth}px` }}
      >
        {leftPanel}
      </div>
      
      {/* Resizer 1 (Left to Middle) */}
      <div 
        onMouseDown={startResizeLeft}
        className="w-1.5 hover:w-2 bg-transparent hover:bg-indigo-500/40 cursor-col-resize transition-all z-20 flex-shrink-0 border-r border-[rgba(255,255,255,0.08)]"
        title="Drag to resize Chat panel"
      />

      {/* Middle Panel: File Explorer */}
      <div 
        className="bg-[#1a1d24] flex flex-col"
        style={{ width: `${middleWidth}px` }}
      >
        {middlePanel}
      </div>
      
      {/* Resizer 2 (Middle to Right) */}
      <div 
        onMouseDown={startResizeMiddle}
        className="w-1.5 hover:w-2 bg-transparent hover:bg-indigo-500/40 cursor-col-resize transition-all z-20 flex-shrink-0 border-r border-[rgba(255,255,255,0.08)]"
        title="Drag to resize Explorer panel"
      />

      {/* Right Panel: Editor & Preview */}
      <div className="flex-1 min-w-0 flex flex-col bg-[#0f1115] relative">
        {rightPanel}
      </div>
    </div>
  );
}
