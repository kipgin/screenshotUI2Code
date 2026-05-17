import React, { useState, useEffect } from 'react';
import { useFileStore } from '@/store/useFileStore';
import { useDiffStore } from '@/store/useDiffStore';
import Editor, { DiffEditor } from '@monaco-editor/react';
import { Check, X, Code2, Eye } from 'lucide-react';
import { useChatStore } from '@/store/useChatStore';

export function EditorPanel() {
  const { activeFilePath, activeFileContent, setActiveContent, saveFile, files } = useFileStore();
  const { pendingDiffs, resolveDiff } = useDiffStore();
  const { sessionId } = useChatStore();
  const [activeTab, setActiveTab] = useState<'code' | 'diff' | 'preview'>('code');

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setActiveContent(value);
    }
  };

  const handleSave = () => {
    if (sessionId && activeFilePath) {
      saveFile(sessionId, activeFileContent);
    }
  };

  const [inlinedHtml, setInlinedHtml] = useState('');
  const [previewError, setPreviewError] = useState('');

  useEffect(() => {
    if (activeTab !== 'preview' || !sessionId) return;

    const findIndexHtml = (nodes: any[]): string | null => {
      for (const node of nodes) {
        if (!node.isDir && node.name === 'index.html') return node.path;
        if (node.isDir && node.children) {
          const found = findIndexHtml(node.children);
          if (found) return found;
        }
      }
      return null;
    };

    const findAnyHtml = (nodes: any[]): string | null => {
      for (const node of nodes) {
        if (!node.isDir && node.name.endsWith('.html')) return node.path;
        if (node.isDir && node.children) {
          const found = findAnyHtml(node.children);
          if (found) return found;
        }
      }
      return null;
    };

    const activeIsHtml = activeFilePath?.endsWith('.html') || activeFileContent.toLowerCase().includes('<html');

    const compileHtml = async (htmlPath: string, htmlContent: string) => {
      let compiled = htmlContent;
      const { getFile } = await import('@/api/workspace');

      // 1. Inline CSS stylesheets: <link ... href="*.css" ...>
      const linkRegex = /<link\s+[^>]*href=["']([^"']+\.css)["'][^>]*>/gi;
      let match;
      const cssReplacements: { tag: string; path: string }[] = [];
      // Re-run regex match iteratively
      const tempHtmlForCss = htmlContent;
      while ((match = linkRegex.exec(tempHtmlForCss)) !== null) {
        cssReplacements.push({ tag: match[0], path: match[1] });
      }

      for (const replacement of cssReplacements) {
        try {
          let cssContent = '';
          // Resolve relative path matches for active file
          const isActiveCss = activeFilePath && (
            activeFilePath === replacement.path || 
            activeFilePath.endsWith('/' + replacement.path) ||
            replacement.path.endsWith('/' + activeFilePath)
          );

          if (isActiveCss) {
            cssContent = activeFileContent;
          } else {
            cssContent = await getFile(sessionId, replacement.path);
          }
          compiled = compiled.replace(replacement.tag, `<style>${cssContent}</style>`);
        } catch (e) {
          console.warn(`Preview: failed to inline css ${replacement.path}`, e);
        }
      }

      // 2. Inline JS scripts: <script ... src="*.js" ...></script>
      const scriptRegex = /<script\s+[^>]*src=["']([^"']+\.js)["'][^>]*>\s*<\/script>/gi;
      const jsReplacements: { tag: string; path: string }[] = [];
      const tempHtmlForJs = htmlContent;
      while ((match = scriptRegex.exec(tempHtmlForJs)) !== null) {
        jsReplacements.push({ tag: match[0], path: match[1] });
      }

      for (const replacement of jsReplacements) {
        try {
          let jsContent = '';
          const isActiveJs = activeFilePath && (
            activeFilePath === replacement.path || 
            activeFilePath.endsWith('/' + replacement.path) ||
            replacement.path.endsWith('/' + activeFilePath)
          );

          if (isActiveJs) {
            jsContent = activeFileContent;
          } else {
            jsContent = await getFile(sessionId, replacement.path);
          }
          compiled = compiled.replace(replacement.tag, `<script>${jsContent}</script>`);
        } catch (e) {
          console.warn(`Preview: failed to inline js ${replacement.path}`, e);
        }
      }

      setInlinedHtml(compiled);
      setPreviewError('');
    };

    if (activeIsHtml && activeFilePath) {
      compileHtml(activeFilePath, activeFileContent);
    } else {
      // Find an HTML file in the workspace to serve as the preview host
      const htmlPath = findIndexHtml(files) || findAnyHtml(files);
      if (htmlPath) {
        import('@/api/workspace').then(({ getFile }) => {
          getFile(sessionId, htmlPath)
            .then(content => {
              compileHtml(htmlPath, content);
            })
            .catch(err => {
              console.error('Preview: failed to fetch base HTML:', err);
              setPreviewError('Failed to fetch base HTML for preview.');
            });
        });
      } else {
        setInlinedHtml('');
        setPreviewError('No HTML files found in the workspace to preview.');
      }
    }
  }, [activeTab, activeFilePath, activeFileContent, files, sessionId]);

  const pendingDiff = pendingDiffs.length > 0 ? pendingDiffs[0] : null;

  return (
    <div className="flex flex-col h-full relative">
      {/* Header Tabs */}
      <div className="flex items-center justify-between px-4 border-b border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] h-12">
        <div className="flex items-center gap-2 h-full">
          <button 
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-2 px-3 h-full text-sm font-medium border-b-2 transition-colors ${activeTab === 'code' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
          >
            <Code2 size={16} /> Code
          </button>
          <button 
            onClick={() => setActiveTab('diff')}
            className={`flex items-center gap-2 px-3 h-full text-sm font-medium border-b-2 transition-colors ${activeTab === 'diff' ? 'border-amber-500 text-amber-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
          >
            <span className="relative">
              Diffs
              {pendingDiffs.length > 0 && (
                <span className="absolute -top-1 -right-3 w-4 h-4 bg-amber-500 text-black text-[10px] font-bold rounded-full flex items-center justify-center">
                  {pendingDiffs.length}
                </span>
              )}
            </span>
          </button>
          <button 
            onClick={() => setActiveTab('preview')}
            className={`flex items-center gap-2 px-3 h-full text-sm font-medium border-b-2 transition-colors ${activeTab === 'preview' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
          >
            <Eye size={16} /> Preview
          </button>
        </div>

        {activeTab === 'code' && activeFilePath && (
          <button onClick={handleSave} className="btn-secondary text-xs px-3 py-1.5 h-8">
            Save File
          </button>
        )}
      </div>

      {/* Editor Content */}
      <div className="flex-1 min-h-0 bg-[#1e1e1e]">
        {activeTab === 'code' && (
          activeFilePath ? (
            <Editor
              height="100%"
              theme="vs-dark"
              path={activeFilePath}
              value={activeFileContent}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                padding: { top: 16 },
                scrollBeyondLastLine: false,
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              Select a file to view code
            </div>
          )
        )}

        {activeTab === 'diff' && (
          pendingDiff ? (
            <div className="flex flex-col h-full">
              <div className="p-3 bg-[rgba(245,158,11,0.1)] border-b border-[rgba(245,158,11,0.2)] flex items-center justify-between">
                <div className="text-sm">
                  <span className="text-gray-400">Proposed changes to: </span>
                  <span className="font-mono text-amber-400">{pendingDiff.path}</span>
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => resolveDiff(pendingDiff.path, 'rejected')}
                    className="flex items-center gap-1 px-3 py-1.5 rounded bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors text-xs font-medium"
                  >
                    <X size={14} /> Reject
                  </button>
                  <button 
                    onClick={() => resolveDiff(pendingDiff.path, 'accepted')}
                    className="flex items-center gap-1 px-3 py-1.5 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors text-xs font-medium"
                  >
                    <Check size={14} /> Accept
                  </button>
                </div>
              </div>
              <DiffEditor
                height="100%"
                theme="vs-dark"
                original={pendingDiff.oldContent}
                modified={pendingDiff.newContent}
                options={{
                  minimap: { enabled: false },
                  readOnly: true,
                  renderSideBySide: true,
                }}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              No pending diffs from AI.
            </div>
          )
        )}

        {activeTab === 'preview' && (
          <div className="w-full h-full bg-white relative">
            {previewError ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 p-6 text-center bg-[#1e1e1e]">
                <Eye size={48} className="opacity-30 mb-2 text-rose-500" />
                <p className="font-semibold text-gray-300">Preview Unavailable</p>
                <p className="text-sm mt-1 max-w-md text-gray-400">{previewError}</p>
              </div>
            ) : inlinedHtml ? (
              <iframe
                title="preview"
                className="w-full h-full border-none"
                srcDoc={inlinedHtml}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 p-6 text-center bg-[#1e1e1e]">
                <Eye size={48} className="opacity-30 mb-2" />
                <p className="font-semibold text-gray-300">No Preview Available</p>
                <p className="text-sm mt-1 max-w-md text-gray-400">
                  Create or select an HTML file to start previewing your design.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
