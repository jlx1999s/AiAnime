import React, { useState } from 'react';
import { Trash2, Search, Plus, Wand2, RefreshCw, Maximize, Save, ChevronLeft, ChevronRight, User, Image as ImageIcon, Video } from 'lucide-react';
import ImagePreviewModal from './ImagePreviewModal';

const Sidebar = ({ characters, scenes, shots, onSceneClick, onCharacterClick, onAddCharacter, onAddScene, onGenerateCharacter, onGenerateScene, onDeleteCharacter, onRegenerateCharacter, onRegenerateScene, onGenerateAllCharacters, onGenerateAllScenes, isGeneratingCharacters, isGeneratingScenes, defaultSceneId, onSetDefaultScene, onImportCharacters, onAutoImportCharacters, onAutoImportScenes, isCollapsed, onToggleCollapse, activeTab, onTabChange, focusShotId }) => {
    const [localTab, setLocalTab] = useState('chars');
    const resolvedTab = activeTab || localTab;
    const setResolvedTab = onTabChange || setLocalTab;
    const [previewUrl, setPreviewUrl] = useState(null);
    const [characterQuery, setCharacterQuery] = useState('');
    const [sceneQuery, setSceneQuery] = useState('');
    const [regeneratingIds, setRegeneratingIds] = useState(new Set());

    const normalize = (value) => (value || '').toString().trim().toLowerCase();
    const filteredCharacters = (characters || []).filter((char) => {
        const query = normalize(characterQuery);
        if (!query) return true;
        return normalize(char?.name).includes(query);
    });
    const filteredScenes = (scenes || []).filter((scene) => {
        const query = normalize(sceneQuery);
        if (!query) return true;
        return normalize(scene?.name).includes(query);
    });

    const safeShots = Array.isArray(shots) ? shots : [];
    const videoShots = safeShots.filter((shot) => {
        const items = Array.isArray(shot?.video_items) ? shot.video_items : [];
        return items.length > 0 || !!shot?.video_url;
    });
    const focusShot = focusShotId ? safeShots.find((shot) => shot.id === focusShotId) : null;
    const focusImageCandidates = focusShot
        ? [
            ...(focusShot.image_url ? [focusShot.image_url] : []),
            ...(Array.isArray(focusShot.image_candidates) ? focusShot.image_candidates.filter((url) => url && url !== focusShot.image_url) : [])
        ]
        : [];
    const focusVideoItems = (() => {
        if (!focusShot) return [];
        const items = Array.isArray(focusShot.video_items) ? focusShot.video_items : [];
        if (items.length > 0) return items;
        if (focusShot.video_url) {
            return [{ id: 'legacy', url: focusShot.video_url, status: focusShot.status, progress: focusShot.video_progress }];
        }
        return [];
    })();

    if (isCollapsed) {
        return (
            <aside className="w-12 border-l border-dark-700 bg-dark-800 flex flex-col flex-shrink-0 items-center py-2 transition-all duration-300">
                <button 
                    onClick={onToggleCollapse}
                    className="mb-4 p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded"
                    title="展开"
                >
                    <ChevronLeft size={20} />
                </button>
                <div className="flex flex-col gap-4 w-full items-center">
                    <button 
                        onClick={() => { onToggleCollapse(); setResolvedTab('chars'); }}
                        className={`p-2 rounded flex flex-col items-center gap-1 ${resolvedTab === 'chars' ? 'text-accent' : 'text-gray-400 hover:text-white'}`}
                        title="角色资产"
                    >
                        <User size={20} />
                        <span className="text-[10px]">角色</span>
                    </button>
                    <button 
                        onClick={() => { onToggleCollapse(); setResolvedTab('scenes'); }}
                        className={`p-2 rounded flex flex-col items-center gap-1 ${resolvedTab === 'scenes' ? 'text-accent' : 'text-gray-400 hover:text-white'}`}
                        title="场景资产"
                    >
                        <ImageIcon size={20} />
                        <span className="text-[10px]">场景</span>
                    </button>
                    <button 
                        onClick={() => { onToggleCollapse(); setResolvedTab('shots'); }}
                        className={`p-2 rounded flex flex-col items-center gap-1 ${resolvedTab === 'shots' ? 'text-accent' : 'text-gray-400 hover:text-white'}`}
                        title="分镜列表"
                    >
                        <ImageIcon size={20} />
                        <span className="text-[10px]">分镜</span>
                    </button>
                    <button 
                        onClick={() => { onToggleCollapse(); setResolvedTab('videos'); }}
                        className={`p-2 rounded flex flex-col items-center gap-1 ${resolvedTab === 'videos' ? 'text-accent' : 'text-gray-400 hover:text-white'}`}
                        title="视频列表"
                    >
                        <Video size={20} />
                        <span className="text-[10px]">视频</span>
                    </button>
                </div>
            </aside>
        );
    }

    return (
        <aside className="w-80 border-l border-dark-700 bg-dark-800 flex flex-col flex-shrink-0 transition-all duration-300">
            <ImagePreviewModal 
                isOpen={!!previewUrl} 
                imageUrl={previewUrl} 
                onClose={() => setPreviewUrl(null)} 
            />
            <div className="flex border-b border-dark-700 relative">
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${resolvedTab === 'chars' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setResolvedTab('chars')}
                >角色资产</button>
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${resolvedTab === 'scenes' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setResolvedTab('scenes')}
                >场景资产</button>
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${resolvedTab === 'shots' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setResolvedTab('shots')}
                >分镜</button>
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${resolvedTab === 'videos' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setResolvedTab('videos')}
                >视频</button>
                
                <button 
                    onClick={onToggleCollapse}
                    className="absolute right-0 top-0 bottom-0 w-8 flex items-center justify-center text-gray-400 hover:text-white hover:bg-dark-700"
                    title="收起"
                >
                    <ChevronRight size={16} />
                </button>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
                {resolvedTab === 'chars' && (
                    <div className="space-y-6">
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <h3 className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                                    角色列表 ({filteredCharacters.length})
                                </h3>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={onGenerateAllCharacters}
                                        disabled={isGeneratingCharacters}
                                        className={`text-[10px] px-2 py-1 rounded transition-colors flex items-center gap-1 ${isGeneratingCharacters ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-dark-700 hover:bg-accent text-gray-300 hover:text-white'}`}
                                        title="为所有角色生成图片（仅未生成的）"
                                    >
                                        {isGeneratingCharacters ? <RefreshCw size={10} className="animate-spin"/> : <Wand2 size={10} />} 
                                        {isGeneratingCharacters ? '生成中...' : '一键生成'}
                                    </button>
                                    <button
                                        onClick={onImportCharacters}
                                        className="bg-dark-700 hover:bg-accent text-gray-300 hover:text-white p-1 rounded transition-colors"
                                        title="导入MD角色"
                                    >
                                        <Save size={14} />
                                    </button>
                                    <button
                                        onClick={onAutoImportCharacters}
                                        className="bg-dark-700 hover:bg-accent text-gray-300 hover:text-white p-1 rounded transition-colors"
                                        title="自动检索导入角色"
                                    >
                                        <Search size={14} />
                                    </button>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            placeholder="搜索..."
                                            value={characterQuery}
                                            onChange={(e) => setCharacterQuery(e.target.value)}
                                            className="bg-dark-900 text-xs px-2 py-1 pl-6 rounded w-24 border border-dark-700 focus:border-accent outline-none"
                                        />
                                        <Search size={10} className="absolute left-1.5 top-1.5 text-gray-500"/>
                                    </div>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                {filteredCharacters.map(char => {
                                    const isGenerating = char?.status === 'generating' || regeneratingIds.has(char.id);
                                    return (
                                        <div 
                                            key={char.id} 
                                            className="flex flex-col items-center gap-1 group cursor-pointer"
                                            onClick={() => onCharacterClick && onCharacterClick(char.id)}
                                        >
                                            <div className="w-16 h-16 rounded overflow-hidden bg-dark-600 border border-transparent group-hover:border-accent relative">
                                                <img src={char.avatar_url || char.avatar} alt={char.name} className="w-full h-full object-cover"/>
                                                {isGenerating && (
                                                    <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-1">
                                                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-transparent border-t-accent border-r-accent"></div>
                                                        <span className="text-[10px] text-gray-200">生成中...</span>
                                                    </div>
                                                )}
                                                <div className="absolute top-0 right-0 hidden group-hover:flex">
                                                    <button 
                                                        className="p-0.5 bg-black/50 hover:bg-black/70 text-white"
                                                        onClick={(e) => { e.stopPropagation(); setPreviewUrl(char.avatar_url || char.avatar); }}
                                                        title="放大查看"
                                                    >
                                                        <Maximize size={10} />
                                                    </button>
                                                    <button 
                                                        className={`p-0.5 bg-black/50 hover:bg-black/70 text-white ${isGenerating ? 'cursor-not-allowed' : ''}`}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            if (isGenerating) return;
                                                            setRegeneratingIds(prev => {
                                                                const next = new Set(prev);
                                                                next.add(char.id);
                                                                return next;
                                                            });
                                                            Promise.resolve(onRegenerateCharacter && onRegenerateCharacter(char))
                                                                .finally(() => {
                                                                    setRegeneratingIds(prev => {
                                                                        const next = new Set(prev);
                                                                        next.delete(char.id);
                                                                        return next;
                                                                    });
                                                                });
                                                        }}
                                                        title="重新生成图片"
                                                    >
                                                        <RefreshCw size={10} className={isGenerating ? 'animate-spin' : ''} />
                                                    </button>
                                                    <button 
                                                        className="p-0.5 bg-black/50 hover:bg-black/70 text-red-400 rounded-bl"
                                                        onClick={(e) => { e.stopPropagation(); onDeleteCharacter && onDeleteCharacter(char.id); }}
                                                        title="删除角色"
                                                    >
                                                        <Trash2 size={10}/>
                                                    </button>
                                                </div>
                                            </div>
                                            <span className="text-[10px] text-gray-400 truncate w-full text-center">{char.name}</span>
                                        </div>
                                    );
                                })}
                                
                                {/* Add Character Buttons */}
                                <div 
                                    className="flex flex-col items-center gap-1 cursor-pointer hover:text-accent group"
                                    onClick={onAddCharacter}
                                >
                                    <div className="w-16 h-16 rounded border border-dashed border-dark-600 flex items-center justify-center group-hover:border-accent group-hover:bg-dark-700 transition-colors">
                                        <Plus size={24}/>
                                    </div>
                                    <span className="text-[10px] text-gray-400 group-hover:text-accent">上传角色</span>
                                </div>
                                <div 
                                    className="flex flex-col items-center gap-1 cursor-pointer hover:text-accent group"
                                    onClick={onGenerateCharacter}
                                >
                                    <div className="w-16 h-16 rounded border border-dashed border-dark-600 flex items-center justify-center group-hover:border-accent group-hover:bg-dark-700 transition-colors">
                                        <Wand2 size={24}/>
                                    </div>
                                    <span className="text-[10px] text-gray-400 group-hover:text-accent">生成角色</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                {resolvedTab === 'scenes' && (
                     <div className="space-y-6">
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <h3 className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                                    场景列表 ({filteredScenes.length})
                                </h3>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={onGenerateAllScenes}
                                        disabled={isGeneratingScenes}
                                        className={`text-[10px] px-2 py-1 rounded transition-colors flex items-center gap-1 ${isGeneratingScenes ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-dark-700 hover:bg-accent text-gray-300 hover:text-white'}`}
                                        title="为所有场景生成图片（仅未生成的）"
                                    >
                                        {isGeneratingScenes ? <RefreshCw size={10} className="animate-spin"/> : <Wand2 size={10} />} 
                                        {isGeneratingScenes ? '生成中...' : '一键生成'}
                                    </button>
                                    <button
                                        onClick={onAutoImportScenes}
                                        className="bg-dark-700 hover:bg-accent text-gray-300 hover:text-white p-1 rounded transition-colors"
                                        title="自动检索导入场景"
                                    >
                                        <Search size={14} />
                                    </button>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            placeholder="搜索..."
                                            value={sceneQuery}
                                            onChange={(e) => setSceneQuery(e.target.value)}
                                            className="bg-dark-900 text-xs px-2 py-1 pl-6 rounded w-24 border border-dark-700 focus:border-accent outline-none"
                                        />
                                        <Search size={10} className="absolute left-1.5 top-1.5 text-gray-500"/>
                                    </div>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                {filteredScenes.map(scene => {
                                    const isGenerating = scene?.status === 'generating' || regeneratingIds.has(scene.id);
                                    return (
                                        <div 
                                            key={scene.id} 
                                            className="flex flex-col gap-1 group cursor-pointer"
                                            onClick={() => onSceneClick && onSceneClick(scene.id)}
                                        >
                                            <div className="aspect-video rounded overflow-hidden bg-dark-600 border border-transparent group-hover:border-accent relative">
                                                {scene.image_url ? (
                                                    <img src={scene.image_url} alt={scene.name} className="w-full h-full object-cover"/>
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center text-dark-500 text-xs">暂无图片</div>
                                                )}
                                                {isGenerating && (
                                                    <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-1">
                                                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-transparent border-t-accent border-r-accent"></div>
                                                        <span className="text-[10px] text-gray-200">生成中...</span>
                                                    </div>
                                                )}
                                                <div className="absolute top-1 right-1 hidden group-hover:flex gap-1">
                                                    <button 
                                                        className={`p-1 ${defaultSceneId === scene.id ? 'bg-accent text-white' : 'bg-black/50 hover:bg-black/70 text-white'} rounded`}
                                                        onClick={(e) => { e.stopPropagation(); onSetDefaultScene && onSetDefaultScene(scene.id); }}
                                                        title={defaultSceneId === scene.id ? "取消默认参考图" : "设为默认参考图"}
                                                    >
                                                        <span className="text-[10px] font-bold">Ref</span>
                                                    </button>
                                                    <button 
                                                        className="p-1 bg-black/50 hover:bg-black/70 text-white rounded"
                                                        onClick={(e) => { e.stopPropagation(); setPreviewUrl(scene.image_url); }}
                                                        title="放大查看"
                                                    >
                                                        <Maximize size={12} />
                                                    </button>
                                                    <button 
                                                        className={`p-1 bg-black/50 hover:bg-black/70 text-white rounded ${isGenerating ? 'cursor-not-allowed' : ''}`}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            if (isGenerating) return;
                                                            setRegeneratingIds(prev => {
                                                                const next = new Set(prev);
                                                                next.add(scene.id);
                                                                return next;
                                                            });
                                                            Promise.resolve(onRegenerateScene && onRegenerateScene(scene))
                                                                .finally(() => {
                                                                    setRegeneratingIds(prev => {
                                                                        const next = new Set(prev);
                                                                        next.delete(scene.id);
                                                                        return next;
                                                                    });
                                                                });
                                                        }}
                                                        title="重新生成图片"
                                                    >
                                                        <RefreshCw size={12} className={isGenerating ? 'animate-spin' : ''} />
                                                    </button>
                                                </div>
                                                {defaultSceneId === scene.id && (
                                                    <div className="absolute top-1 left-1 bg-accent text-white text-[8px] px-1 rounded shadow-sm font-bold">
                                                        默认参考
                                                    </div>
                                                )}
                                            </div>
                                            <span className="text-[10px] text-gray-400 truncate w-full">{scene.name}</span>
                                        </div>
                                    );
                                })}

                                {/* Add Scene Buttons */}
                                <div 
                                    className="flex flex-col gap-1 cursor-pointer hover:text-accent group"
                                    onClick={onAddScene}
                                >
                                    <div className="aspect-video rounded border border-dashed border-dark-600 flex items-center justify-center group-hover:border-accent group-hover:bg-dark-700 transition-colors">
                                        <Plus size={24}/>
                                    </div>
                                    <span className="text-[10px] text-gray-400 group-hover:text-accent text-center">上传场景</span>
                                </div>
                                <div 
                                    className="flex flex-col gap-1 cursor-pointer hover:text-accent group"
                                    onClick={onGenerateScene}
                                >
                                    <div className="aspect-video rounded border border-dashed border-dark-600 flex items-center justify-center group-hover:border-accent group-hover:bg-dark-700 transition-colors">
                                        <Wand2 size={24}/>
                                    </div>
                                    <span className="text-[10px] text-gray-400 group-hover:text-accent text-center">生成场景</span>
                                </div>
                            </div>
                        </div>
                     </div>
                )}
                {resolvedTab === 'shots' && (
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <h3 className="text-xs font-bold text-gray-500 uppercase">
                                分镜候选 ({focusImageCandidates.length})
                            </h3>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {focusImageCandidates.length > 0 ? focusImageCandidates.map((url, index) => (
                                <div
                                    key={`${focusShotId}-${index}`}
                                    className="flex flex-col gap-1 group cursor-pointer"
                                    onClick={() => setPreviewUrl(url)}
                                >
                                    <div className="aspect-video rounded overflow-hidden bg-dark-600 border border-transparent group-hover:border-accent relative">
                                        <img src={url} alt={`shot-${index + 1}`} className="w-full h-full object-cover" />
                                    </div>
                                    <span className="text-[10px] text-gray-400 truncate w-full">候选 {index + 1}</span>
                                </div>
                            )) : (
                                <div className="col-span-2 text-xs text-dark-500">未选择分镜</div>
                            )}
                        </div>
                    </div>
                )}
                {resolvedTab === 'videos' && (
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <h3 className="text-xs font-bold text-gray-500 uppercase">
                                视频候选 ({focusVideoItems.length})
                            </h3>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {focusVideoItems.length > 0 ? focusVideoItems.map((item, index) => (
                                <div
                                    key={`${item.id || 'video'}-${index}`}
                                    className="flex flex-col gap-1 group"
                                >
                                    <div className="aspect-video rounded overflow-hidden bg-black border border-transparent group-hover:border-accent relative">
                                        {item?.url ? (
                                            <video src={item.url} className="w-full h-full object-cover" controls />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-dark-500 text-xs">生成中</div>
                                        )}
                                    </div>
                                    <span className="text-[10px] text-gray-400 truncate w-full">候选 {index + 1}</span>
                                </div>
                            )) : (
                                <div className="col-span-2 text-xs text-dark-500">未选择视频</div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </aside>
    );
};

export default Sidebar;
