import React, { useEffect, useState, useRef } from 'react';
import { Plus, Trash2, Image, Video, MoveUp, MoveDown, Maximize, Upload, ChevronLeft, ChevronRight } from 'lucide-react';
import ImagePreviewModal from './ImagePreviewModal';
import { ApiService } from '../services/api';

const updatePromptWithAsset = (currentPrompt, action, assetType, asset, oldAsset) => {
    let newPrompt = currentPrompt || "";
    
    // Helper to escape regex special chars
    const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    if (action === 'add') {
        const assetName = asset?.name;
        const assetPrompt = asset?.prompt;
        if (!assetName) return newPrompt;

        // Check if already exists to avoid duplication
        const exists = newPrompt.includes(`[${assetName}`);
        
        if (!exists) {
            // Append at the end
            const tag = assetPrompt ? ` [${assetName}: ${assetPrompt}]` : ` [${assetName}]`;
            newPrompt = newPrompt.trimEnd() + tag;
        }
    } else if (action === 'remove') {
        const assetName = asset?.name;
        if (!assetName) return newPrompt;
        
        // Remove [Name: ...] or [Name]
        const escapedName = escapeRegExp(assetName);
        const regex = new RegExp(`\\s*\\[${escapedName}(:.*?)?\\]`, 'g');
        newPrompt = newPrompt.replace(regex, '');
    } else if (action === 'replace') {
        // Remove old asset
        if (oldAsset) {
            newPrompt = updatePromptWithAsset(newPrompt, 'remove', assetType, oldAsset);
        }
        // Add new asset
        if (asset) {
            newPrompt = updatePromptWithAsset(newPrompt, 'add', assetType, asset);
        }
    }
    
    return newPrompt.trim();
};

const ShotItem = ({ shot, index, onDelete, onUpdate, onGenerate, onDeleteShotImage, onDeleteVideo, onMoveUp, onMoveDown, allCharacters, onCharacterClick, allScenes, onSceneClick, onShotImageClick, onSelectCandidate, isSelected, onSelect, defaultImageCount, projectId }) => {
    const [candidateCount, setCandidateCount] = useState(defaultImageCount || 1);
    const customImageInputRef = useRef(null);

    const handleCustomImageUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !projectId) return;
        
        try {
            const result = await ApiService.uploadFile(file, projectId);
            if (result && result.url) {
                 onUpdate(shot.id, { ...shot, custom_image_url: result.url });
            }
        } catch (error) {
            console.error("Custom image upload failed", error);
            alert("上传失败");
        }
        e.target.value = null;
    };

    useEffect(() => {
        if (defaultImageCount) {
            setCandidateCount(defaultImageCount);
        }
    }, [defaultImageCount]);
    const [previewUrl, setPreviewUrl] = useState(null);
    const imageScrollRef = useRef(null);
    const videoScrollRef = useRef(null);

    const videoItems = Array.isArray(shot.video_items) && shot.video_items.length
        ? shot.video_items
        : (shot.video_url ? [{ id: 'legacy', url: shot.video_url, progress: shot.video_progress, status: shot.status }] : []);
    const [activeVideoId, setActiveVideoId] = useState(videoItems[0]?.id ?? null);

    const scrollContainer = (ref, direction) => {
        if (ref.current) {
            const scrollAmount = 300;
            ref.current.scrollBy({
                left: direction === 'left' ? -scrollAmount : scrollAmount,
                behavior: 'smooth'
            });
        }
    };

    useEffect(() => {
        if (!videoItems.length) {
            if (activeVideoId !== null) {
                setActiveVideoId(null);
            }
            return;
        }
        if (!videoItems.some(v => v.id === activeVideoId)) {
            setActiveVideoId(videoItems[0].id);
        }
    }, [videoItems, activeVideoId]);

    return (
        <div className="grid grid-cols-[40px_minmax(260px,2fr)_minmax(180px,1.2fr)_minmax(180px,1.2fr)_minmax(180px,1.2fr)_minmax(240px,1.6fr)_minmax(240px,1.6fr)_40px] gap-4 p-4 border-b border-dark-700 bg-dark-800/30 hover:bg-dark-800 transition-colors group items-start">
            <ImagePreviewModal 
                isOpen={!!previewUrl} 
                imageUrl={previewUrl} 
                onClose={() => setPreviewUrl(null)} 
            />
            {/* Column 1: Index */}
            <div className="flex flex-col items-center gap-2 pt-1">
                <span className="text-xs font-mono text-gray-500 bg-dark-900 px-1.5 py-0.5 rounded-full min-w-[24px] text-center">{index + 1}</span>
                <input 
                    type="checkbox" 
                    className="rounded bg-dark-700 border-dark-600 w-4 h-4 cursor-pointer accent-accent"
                    checked={isSelected || false}
                    onChange={(e) => onSelect && onSelect(e.target.checked)}
                />
            </div>

            {/* Column 2: Script */}
            <div className="space-y-3">
                 <div className="relative">
                     <div className="flex justify-between items-center mb-1">
                       <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">分镜提示词</label>
                       <span className="text-[10px] text-dark-600 cursor-pointer hover:text-accent">AI 优化</span>
                    </div>
                    <textarea 
                        className="w-full bg-dark-900/50 border border-dark-700 rounded p-2 text-sm text-gray-300 focus:border-accent focus:outline-none resize-none h-20 placeholder-gray-700 transition-colors"
                        value={shot.prompt}
                        placeholder="描述画面内容、镜头角度、光影..."
                        onChange={(e) => onUpdate(shot.id, { ...shot, prompt: e.target.value })}
                    />
                </div>
                <div className="relative">
                    <div className="flex justify-between items-center mb-1">
                       <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">视频提示词</label>
                    </div>
                    <textarea 
                        className="w-full bg-dark-900/50 border border-dark-700 rounded p-2 text-sm text-gray-300 focus:border-accent focus:outline-none resize-none h-16 placeholder-gray-700 transition-colors"
                        value={shot.audio_prompt || ''}
                        placeholder="描述视频风格、运动、节奏、氛围等..."
                        onChange={(e) => onUpdate(shot.id, { ...shot, audio_prompt: e.target.value })}
                    />
                </div>
            </div>

            {/* Column 3: Characters */}
            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">出场人物</label>
                 </div>
                 <div className="grid grid-cols-3 gap-2">
                    {shot.characters.map((charId, i) => {
                        const char = allCharacters?.find(c => c.id === charId);
                        const avatarUrl = char?.avatar_url || char?.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${charId}`;
                        
                        return (
                            <div 
                                key={i} 
                                className="aspect-square rounded bg-dark-700 border border-dark-600 overflow-hidden relative group/char cursor-pointer"
                                onClick={() => setPreviewUrl(avatarUrl)}
                                title={char?.name || "未知角色"}
                            >
                                <img src={avatarUrl} className="w-full h-full object-cover" alt="character"/>
                                <div className="absolute inset-0 bg-black/60 hidden group-hover/char:flex items-center justify-center pointer-events-none">
                                    <Maximize size={16} className="text-white"/>
                                </div>
                                <div className="absolute top-0 right-0 flex gap-1 p-1 opacity-0 group-hover/char:opacity-100 transition-opacity">
                                    <button
                                        className="p-1 bg-black/50 hover:bg-black/70 text-white rounded"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onCharacterClick && onCharacterClick(charId);
                                        }}
                                        title="更换图片"
                                    >
                                        <Upload size={10} />
                                    </button>
                                    <button
                                        className="p-1 bg-black/50 hover:bg-black/70 text-red-400 rounded"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (confirm(`确定移除 ${char?.name || '该角色'} 出场吗？`)) {
                                                const newCharacters = (shot.characters || []).filter(id => id !== charId);
                                                const newPrompt = updatePromptWithAsset(shot.prompt, 'remove', 'character', char);
                                                const newAudioPrompt = updatePromptWithAsset(shot.audio_prompt, 'remove', 'character', char);
                                                onUpdate && onUpdate(shot.id, { ...shot, characters: newCharacters, prompt: newPrompt, audio_prompt: newAudioPrompt });
                                            }
                                        }}
                                        title="移除角色"
                                    >
                                        <Trash2 size={10} />
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                    <div className="aspect-square rounded border border-dashed border-dark-600 flex items-center justify-center hover:bg-dark-700 text-dark-500 hover:text-accent hover:border-accent transition-colors relative">
                        <Plus size={14} className="pointer-events-none"/>
                        <select
                            className="opacity-0 absolute inset-0 w-full h-full cursor-pointer appearance-none"
                            onChange={(e) => {
                                if (e.target.value) {
                                    const newCharId = e.target.value;
                                    if (!shot.characters.includes(newCharId)) {
                                        const charToAdd = allCharacters?.find(c => c.id === newCharId);
                                        const newPrompt = updatePromptWithAsset(shot.prompt, 'add', 'character', charToAdd);
                                        const newAudioPrompt = updatePromptWithAsset(shot.audio_prompt, 'add', 'character', charToAdd);
                                        onUpdate(shot.id, { ...shot, characters: [...shot.characters, newCharId], prompt: newPrompt, audio_prompt: newAudioPrompt });
                                    }
                                    e.target.value = "";
                                }
                            }}
                            value=""
                            title="添加角色"
                        >
                            <option value="" disabled>添加角色...</option>
                            {allCharacters?.filter(c => !shot.characters.includes(c.id)).map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                 </div>
            </div>

            {/* Column 4: Scene */}
            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">场景</label>
                    {shot.scene_id && allScenes && (
                        <select
                            className="bg-dark-900 border border-dark-700 rounded text-[10px] text-gray-400 px-1 py-0.5 outline-none focus:border-accent appearance-none truncate"
                            onChange={(e) => {
                                if (e.target.value) {
                                    const nextId = e.target.value;
                                    if (nextId !== shot.scene_id) {
                                        const oldScene = allScenes?.find(s => s.id === shot.scene_id);
                                        const newScene = allScenes?.find(s => s.id === nextId);
                                        const newPrompt = updatePromptWithAsset(shot.prompt, 'replace', 'scene', newScene, oldScene);
                                        const newAudioPrompt = updatePromptWithAsset(shot.audio_prompt, 'replace', 'scene', newScene, oldScene);
                                        onUpdate(shot.id, { ...shot, scene_id: nextId, use_scene_ref: true, prompt: newPrompt, audio_prompt: newAudioPrompt });
                                    }
                                    e.target.value = "";
                                }
                            }}
                            value=""
                            title="切换场景"
                        >
                            <option value="" disabled>切换场景...</option>
                            {allScenes.filter(s => s.id !== shot.scene_id).map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    )}
                 </div>
                 
                 {shot.scene_id && allScenes ? (
                     <div 
                        className="aspect-video w-full rounded overflow-hidden border border-dark-700 relative group/scene cursor-pointer"
                        onClick={() => {
                            const scene = allScenes.find(s => s.id === shot.scene_id);
                            if (scene?.image_url) setPreviewUrl(scene.image_url);
                        }}
                        title="点击放大查看"
                     >
                        {(() => {
                            const scene = allScenes.find(s => s.id === shot.scene_id);
                            return scene?.image_url ? (
                                <img src={scene.image_url} className="w-full h-full object-cover" alt="scene ref" />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center bg-dark-800 text-dark-500">
                                    <Image size={20}/>
                                </div>
                            );
                        })()}
                        
                        <div className="absolute inset-0 bg-black/50 hidden group-hover/scene:flex items-center justify-center pointer-events-none">
                            <Maximize size={20} className="text-white"/>
                        </div>

                        <div className="absolute top-2 right-2 flex gap-1 hidden group-hover/scene:flex">
                             <button
                                className="p-1.5 bg-black/50 hover:bg-black/70 text-white rounded"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onSceneClick && onSceneClick(shot.scene_id);
                                }}
                                title="更换场景图片"
                            >
                                <Upload size={14} />
                            </button>
                        </div>
                        
                        <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-1">
                            <div className="text-[10px] text-gray-200 truncate text-center">
                                {allScenes.find(s => s.id === shot.scene_id)?.name || "未知场景"}
                            </div>
                        </div>
                     </div>
                 ) : (
                    <div className="flex gap-1">
                        <select 
                            className="flex-1 bg-dark-900 border border-dark-700 rounded text-xs text-gray-400 p-1 outline-none focus:border-accent appearance-none truncate"
                            onChange={(e) => {
                                const nextId = e.target.value;
                                const oldScene = allScenes?.find(s => s.id === shot.scene_id);
                                const newScene = allScenes?.find(s => s.id === nextId);
                                const newPrompt = updatePromptWithAsset(shot.prompt, 'replace', 'scene', newScene, oldScene);
                                const newAudioPrompt = updatePromptWithAsset(shot.audio_prompt, 'replace', 'scene', newScene, oldScene);
                                onUpdate(shot.id, { ...shot, scene_id: nextId, use_scene_ref: true, prompt: newPrompt, audio_prompt: newAudioPrompt });
                            }}
                            value=""
                        >
                            <option value="" disabled>选择场景...</option>
                            {allScenes?.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    </div>
                 )}
                 
                 {shot.scene_id && (
                     <div className="flex items-center gap-2 mt-1 px-1">
                        <input 
                            type="checkbox" 
                            id={`use-scene-ref-${shot.id}`}
                            checked={shot.use_scene_ref !== false}
                            onChange={(e) => onUpdate(shot.id, { ...shot, use_scene_ref: e.target.checked })}
                            className="rounded bg-dark-700 border-dark-600 w-3 h-3 cursor-pointer accent-accent"
                        />
                        <label htmlFor={`use-scene-ref-${shot.id}`} className="text-[10px] text-gray-400 cursor-pointer select-none hover:text-gray-300">
                            作为参考图
                        </label>
                     </div>
                 )}
            </div>

            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">自定义参考图</label>
                 </div>
                 
                 <input 
                     type="file" 
                     ref={customImageInputRef} 
                     className="hidden" 
                     accept="image/*"
                     onChange={handleCustomImageUpload}
                 />

                 {shot.custom_image_url ? (
                     <div 
                        className="aspect-video w-full rounded overflow-hidden border border-dark-700 relative group/custom cursor-pointer"
                        onClick={() => customImageInputRef.current?.click()}
                        title="点击更换自定义参考图"
                     >
                        <img src={shot.custom_image_url} className="w-full h-full object-cover" alt="custom ref" />
                        <div className="absolute inset-0 bg-black/50 hidden group-hover/custom:flex items-center justify-center">
                            <span className="text-xs text-white">更换图片</span>
                        </div>
                        <button
                            className="absolute top-0 right-0 p-1 bg-black/50 rounded-bl hidden group-hover/custom:block"
                            onClick={(e) => {
                                e.stopPropagation();
                                if (confirm('确定移除自定义参考图吗？')) {
                                    onUpdate(shot.id, { ...shot, custom_image_url: null });
                                }
                            }}
                            title="移除参考图"
                        >
                            <Trash2 size={10} className="text-red-400"/>
                        </button>
                     </div>
                 ) : (
                     <div 
                         className="aspect-video w-full rounded border border-dashed border-dark-600 flex items-center justify-center gap-1 cursor-pointer hover:bg-dark-800 text-dark-500 hover:text-gray-400 transition-colors"
                         onClick={() => customImageInputRef.current?.click()}
                     >
                         <Upload size={14}/>
                         <span className="text-[10px]">上传参考图</span>
                     </div>
                 )}
            </div>

            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">分镜</label>
                    <div className="flex items-center gap-1 text-[10px] text-dark-500">
                        {/* Panel Layout Selector */}
                        <select
                            value={shot.panel_layout || "1-panel"}
                            onChange={(e) => onUpdate(shot.id, { ...shot, panel_layout: e.target.value })}
                            className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[10px] text-gray-400 outline-none focus:border-accent mr-1"
                        >
                            <option value="1-panel">单图</option>
                            <option value="2-panel">二宫格</option>
                            <option value="3-panel">三宫格</option>
                            <option value="4-panel">四宫格</option>
                        </select>

                        <input
                            type="number"
                            min="1"
                            max="8"
                            value={candidateCount}
                            onChange={(e) => {
                                const v = parseInt(e.target.value || '0', 10);
                                if (!isNaN(v)) {
                                    setCandidateCount(Math.max(1, Math.min(8, v)));
                                } else {
                                    setCandidateCount(1);
                                }
                            }}
                            className="w-10 bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[10px] text-gray-400 outline-none focus:border-accent"
                        />
                        <span>张</span>
                        <button
                            type="button"
                            className="cursor-pointer hover:text-accent"
                            onClick={() => onGenerate && onGenerate(shot.id, 'image', candidateCount)}
                        >
                            生成
                        </button>
                    </div>
                 </div>

                {shot.image_url ? (
                    <div 
                        className="aspect-video w-full rounded overflow-hidden border border-dark-700 relative group/image cursor-pointer"
                        onClick={() => setPreviewUrl(shot.image_url)}
                    >
                        <img src={shot.image_url} className="w-full h-full object-cover" alt="scene"/>
                        <div 
                            className="absolute inset-0 bg-black/50 hidden group-hover/image:flex items-center justify-center pointer-events-none" 
                        >
                            <Maximize size={24} className="text-white"/>
                        </div>
                        <button
                            className="absolute top-2 right-2 p-1.5 bg-black/50 hover:bg-black/70 text-white rounded hidden group-hover/image:block z-10"
                            onClick={(e) => {
                                e.stopPropagation();
                                onShotImageClick && onShotImageClick(shot.id);
                            }}
                            title="更换图片"
                        >
                            <Upload size={16} />
                        </button>
                        <button
                            className="absolute top-2 left-2 p-1.5 bg-black/50 hover:bg-black/70 text-white rounded hidden group-hover/image:block z-10"
                            onClick={(e) => {
                                e.stopPropagation();
                                if (confirm('确定删除当前分镜图吗？')) {
                                    onDeleteShotImage && onDeleteShotImage(shot.id, shot.image_url);
                                }
                            }}
                            title="删除分镜"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>
                ) : shot.status === 'generating' ? (
                    <div className="aspect-video w-full rounded overflow-hidden border border-dark-700 relative flex items-center justify-center bg-dark-900">
                        <img 
                            src="https://placehold.co/600x340/1a1b1e/666?text=Generating..." 
                            className="w-full h-full object-cover opacity-50" 
                            alt="generating"
                        />
                         <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                            <div className="animate-spin rounded-full h-8 w-8 border-2 border-transparent border-t-accent border-r-accent"></div>
                            <span className="text-xs text-gray-300">生成中...</span>
                        </div>
                    </div>
                ) : (
                    <div className="aspect-video w-full rounded border border-dashed border-dark-600 flex flex-col items-center justify-center gap-2 text-dark-500 bg-dark-900/30">
                        <Image size={20}/>
                        <span className="text-xs">暂无分镜，右侧输入数量后点击“生成”</span>
                    </div>
                 )}
                {Array.isArray(shot.image_candidates) && (shot.image_candidates.length > 1 || (shot.image_candidates.length > 0 && shot.status === 'generating')) && (
                    <div className="flex items-center gap-2 pt-1">
                        <button
                            type="button"
                            className="w-6 h-10 flex items-center justify-center rounded border border-dark-700 text-gray-400 hover:text-white hover:border-accent disabled:opacity-40"
                            onClick={() => scrollContainer(imageScrollRef, 'left')}
                            title="向左"
                        >
                            <ChevronLeft size={14} />
                        </button>
                        <div 
                            className="flex gap-2 overflow-x-hidden scroll-smooth" 
                            ref={imageScrollRef}
                        >
                            {shot.image_candidates.map((url, idx) => {
                                const isActive = url === shot.image_url;
                                return (
                                    <button
                                        key={idx}
                                        type="button"
                                        className={`relative w-16 h-10 rounded border ${isActive ? 'border-accent' : 'border-dark-700'} overflow-hidden flex-shrink-0`}
                                        onClick={() => onSelectCandidate && onSelectCandidate(shot.id, url)}
                                    >
                                        <img src={url} alt="candidate" className="w-full h-full object-cover" />
                                        <div className="absolute top-0 right-0 p-0.5 bg-black/60 text-white rounded-bl">
                                            <button
                                                type="button"
                                                className="block"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (confirm('确定删除这张分镜图吗？')) {
                                                        onDeleteShotImage && onDeleteShotImage(shot.id, url);
                                                    }
                                                }}
                                                title="删除分镜"
                                            >
                                                <Trash2 size={10} />
                                            </button>
                                        </div>
                                    </button>
                                );
                            })}
                            {shot.status === 'generating' && (
                                <div className="relative w-16 h-10 rounded border border-dark-700 overflow-hidden flex-shrink-0 flex items-center justify-center bg-dark-900">
                                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-transparent border-t-accent border-r-accent"></div>
                                </div>
                            )}
                        </div>
                        <button
                            type="button"
                            className="w-6 h-10 flex items-center justify-center rounded border border-dark-700 text-gray-400 hover:text-white hover:border-accent disabled:opacity-40"
                            onClick={() => scrollContainer(imageScrollRef, 'right')}
                            title="向右"
                        >
                            <ChevronRight size={14} />
                        </button>
                    </div>
                )}
            </div>

            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">视频</label>
                    {shot.image_url && (
                        <span
                            className="text-[10px] text-dark-500 cursor-pointer hover:text-accent"
                            onClick={() => onGenerate && onGenerate(shot.id, 'video')}
                        >
                            生成视频
                        </span>
                    )}
                 </div>

                {videoItems.length > 0 ? (
                    <div className="space-y-2">
                        {(() => {
                            const activeItem = videoItems.find(v => v.id === activeVideoId) || videoItems[0];
                            return (
                                <div className="aspect-video w-full rounded overflow-hidden border border-accent bg-black relative group/video">
                                    {activeItem?.url ? (
                                        <video src={activeItem.url} className="w-full h-full object-cover" controls />
                                    ) : (
                                        <div className="w-full h-full flex flex-col items-center justify-center gap-2 bg-dark-900/30 text-dark-500">
                                            <Video size={20}/>
                                            <span className="text-[10px]">
                                                {activeItem?.status === 'failed' ? '生成失败' : (activeItem?.progress > 0 ? `生成中 ${activeItem.progress}%` : '生成中...')}
                                            </span>
                                        </div>
                                    )}
                                    <button
                                        className="absolute top-2 right-2 p-1 bg-black/60 hover:bg-black/80 text-white rounded hidden group-hover/video:block"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (activeItem && confirm('确定删除该视频吗？')) {
                                                onDeleteVideo && onDeleteVideo(shot.id, activeItem.id, activeItem.url);
                                            }
                                        }}
                                        title="删除视频"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            );
                        })()}
                        <div className="flex items-center gap-2 pt-1">
                            <button
                                type="button"
                                className="w-6 h-10 flex items-center justify-center rounded border border-dark-700 text-gray-400 hover:text-white hover:border-accent disabled:opacity-40"
                                onClick={() => scrollContainer(videoScrollRef, 'left')}
                                title="向左"
                            >
                                <ChevronLeft size={14} />
                            </button>
                            <div 
                                className="flex gap-2 overflow-x-hidden scroll-smooth"
                                ref={videoScrollRef}
                            >
                                {videoItems.map((item) => {
                                    const isActive = item.id === activeVideoId || (!activeVideoId && videoItems[0]?.id === item.id);
                                    return (
                                    <div 
                                        key={item.id} 
                                        className={`aspect-video w-28 rounded overflow-hidden border bg-black relative transition-all group/video flex-shrink-0 cursor-pointer ${isActive ? 'border-accent scale-100 opacity-100' : 'border-dark-700 scale-[0.94] opacity-70'}`}
                                        onClick={() => setActiveVideoId(item.id)}
                                    >
                                        {item.url ? (
                                            <video src={item.url} className="w-full h-full object-cover" />
                                        ) : (
                                            <div className="w-full h-full flex flex-col items-center justify-center gap-1 bg-dark-900/30 text-dark-500">
                                                <Video size={14}/>
                                                <span className="text-[10px]">
                                                    {item.status === 'failed' ? '失败' : (item.progress > 0 ? `${item.progress}%` : '生成中')}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                );
                                })}
                            </div>
                            <button
                                type="button"
                                className="w-6 h-10 flex items-center justify-center rounded border border-dark-700 text-gray-400 hover:text-white hover:border-accent disabled:opacity-40"
                                onClick={() => scrollContainer(videoScrollRef, 'right')}
                                title="向右"
                            >
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="aspect-video w-full rounded border border-dashed border-dark-600 flex flex-col items-center justify-center gap-2 bg-dark-900/30 relative">
                        {shot.image_url ? (
                            <div className="flex flex-col items-center justify-center gap-2 text-dark-500">
                                <Video size={20}/>
                                <span className="text-xs">{shot.status === 'failed' ? '生成失败' : '点击右上角生成视频'}</span>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center gap-2 text-dark-600">
                                <Video size={20} className="opacity-50"/>
                                <span className="text-[10px]">需先生成图片</span>
                            </div>
                        )}
                    </div>
                 )}
            </div>

            {/* Column 6: Actions */}
            <div className="flex flex-col gap-2 pt-1 items-center">
                <button className="hover:text-white hover:bg-dark-700 p-1 rounded text-gray-500" title="上移" onClick={onMoveUp}><MoveUp size={14}/></button>
                <button className="hover:text-white hover:bg-dark-700 p-1 rounded text-gray-500" title="下移" onClick={onMoveDown}><MoveDown size={14}/></button>
                <button className="hover:text-red-400 hover:bg-dark-700 p-1 rounded mt-2 text-gray-500" onClick={() => onDelete(shot.id)} title="删除"><Trash2 size={14}/></button>
            </div>
        </div>
    );
};

export default ShotItem;
