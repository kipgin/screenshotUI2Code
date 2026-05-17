import React, { useEffect } from 'react';
import { useFileStore } from '@/store/useFileStore';
import { useGitStore } from '@/store/useGitStore';
import { useChatStore } from '@/store/useChatStore';
import { FileNode } from '@/types';
import { Folder, FileCode, ChevronRight, ChevronDown, GitCommit, Trash2, Plus, FolderPlus, CircleDot } from 'lucide-react';

function FileTreeNode({ node, depth = 0 }: { node: FileNode; depth?: number }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isHovered, setIsHovered] = React.useState(false);
  const { sessionId } = useChatStore();
  const { openFile, removeFile, activeFilePath } = useFileStore();

  const isSelected = activeFilePath === node.path;

  const handleClick = () => {
    if (node.isDir) {
      setIsOpen(!isOpen);
    } else {
      if (sessionId) openFile(sessionId, node.path);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (sessionId && window.confirm(`Delete ${node.name}?`)) {
      removeFile(sessionId, node.path);
    }
  };

  return (
    <div>
      <div 
        className={`group flex items-center justify-between py-1 px-2 cursor-pointer rounded-md text-sm transition-colors ${isSelected ? 'bg-indigo-600/20 text-indigo-300' : 'hover:bg-[rgba(255,255,255,0.05)] text-gray-300'}`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={handleClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="flex items-center gap-1.5 overflow-hidden">
          {node.isDir ? (
            isOpen ? <ChevronDown size={14} className="text-gray-500 shrink-0" /> : <ChevronRight size={14} className="text-gray-500 shrink-0" />
          ) : <div className="w-[14px] shrink-0" />}
          
          {node.isDir ? <Folder size={14} className="text-indigo-400 shrink-0" /> : <FileCode size={14} className="text-gray-400 shrink-0" />}
          <span className="truncate">{node.name}</span>
        </div>
        
        {!node.isDir && isHovered && (
          <button 
            onClick={handleDelete}
            className="text-gray-500 hover:text-rose-400 p-0.5 rounded transition-colors"
            title="Delete File"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
      
      {node.isDir && isOpen && node.children && (
        <div>
          {node.children.map(child => (
            <FileTreeNode key={child.path} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ExplorerPanel() {
  const { files, refreshFiles, createFile, createFolder } = useFileStore();
  const { commits, refreshGit, checkoutCommit, activeCommitHash } = useGitStore();
  const { sessionId } = useChatStore();
  const [activeTab, setActiveTab] = React.useState<'files' | 'git'>('files');

  useEffect(() => {
    if (sessionId) {
      refreshFiles(sessionId);
      refreshGit(sessionId);
    }
  }, [sessionId, refreshFiles, refreshGit]);

  const handleCreateFile = () => {
    if (!sessionId) return;
    const fileName = window.prompt('Enter new file name:');
    if (fileName) {
      createFile(sessionId, fileName);
    }
  };

  const handleCreateFolder = () => {
    if (!sessionId) return;
    const folderName = window.prompt('Enter new folder name:');
    if (folderName) {
      createFolder(sessionId, folderName);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)]">
        <button 
          onClick={() => setActiveTab('files')}
          className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider ${activeTab === 'files' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-[rgba(255,255,255,0.03)]' : 'text-gray-500 hover:text-gray-300'}`}
        >
          Files
        </button>
        <button 
          onClick={() => setActiveTab('git')}
          className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider ${activeTab === 'git' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-[rgba(255,255,255,0.03)]' : 'text-gray-500 hover:text-gray-300'}`}
        >
          Git
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {activeTab === 'files' && (
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-center p-2 border-b border-[rgba(255,255,255,0.05)]">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Workspace</span>
              <div className="flex items-center gap-1">
                <button 
                  onClick={handleCreateFile}
                  className="text-gray-400 hover:text-indigo-400 p-1 rounded hover:bg-[rgba(255,255,255,0.05)] transition-colors"
                  title="New File"
                >
                  <Plus size={14} />
                </button>
                <button 
                  onClick={handleCreateFolder}
                  className="text-gray-400 hover:text-indigo-400 p-1 rounded hover:bg-[rgba(255,255,255,0.05)] transition-colors"
                  title="New Folder"
                >
                  <FolderPlus size={14} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto space-y-0.5 p-1 pt-2">
              {files.length === 0 ? (
                <div className="text-center p-4 text-sm text-gray-500">No files in workspace</div>
              ) : (
                files.map(node => <FileTreeNode key={node.path} node={node} />)
              )}
            </div>
          </div>
        )}

        {activeTab === 'git' && (
          <div className="p-4 relative">
            <div className="absolute left-6 top-6 bottom-4 w-px bg-[rgba(255,255,255,0.1)]"></div>
            <div className="space-y-4">
              {commits.length === 0 ? (
                <div className="text-center p-4 text-sm text-gray-500">No commits yet</div>
              ) : (
                commits.map(commit => {
                  const isActive = commit.hash === activeCommitHash;
                  return (
                    <div 
                      key={commit.hash} 
                      className={`relative pl-8 group cursor-pointer ${isActive ? 'opacity-100' : 'opacity-80 hover:opacity-100'}`} 
                      onClick={() => sessionId && checkoutCommit(sessionId, commit.hash)}
                    >
                      {/* Commit Circle */}
                      <div className={`absolute left-[3px] top-1.5 w-3 h-3 rounded-full border-2 transition-colors z-10 ${isActive ? 'bg-emerald-500 border-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-[#1a1d24] border-indigo-500 group-hover:bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.4)]'}`}></div>
                      
                      <div className={`p-3 rounded-lg border transition-all ${isActive ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-[rgba(255,255,255,0.03)] border-[rgba(255,255,255,0.05)] group-hover:bg-[rgba(255,255,255,0.06)]'}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${isActive ? 'text-emerald-300 bg-emerald-500/20' : 'text-indigo-300 bg-indigo-500/10'}`}>{commit.hash.substring(0, 7)}</span>
                          <span className="text-xs text-gray-500 truncate">Checkpoint</span>
                        </div>
                        <p className={`text-sm ${isActive ? 'text-white font-medium' : 'text-gray-200'}`}>{commit.message}</p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
