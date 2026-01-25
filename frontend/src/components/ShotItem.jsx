import React, { useState } from 'react';
import { Plus, Trash2, Image, Play, Video, MoveUp, MoveDown, Maximize } from 'lucide-react';
import ImagePreviewModal from './ImagePreviewModal';

const ShotItem = ({ shot, index, onDelete, onUpdate, onGenerate, onMoveUp, onMoveDown, allCharacters, onCharacterClick, allScenes, onSceneClick, onShotImageClick, onSelectCandidate }) => {
    const [candidateCount, setCandidateCount] = useState(3);
    const [previewUrl, setPreviewUrl] = useState(null);

    return (
        <div className="grid grid-cols-[40px_minmax(200px,1.5fr)_1fr_1fr_1.5fr_1.5fr_40px] gap-4 p-4 border-b border-dark-700 bg-dark-800/30 hover:bg-dark-800 transition-colors group items-start">
            <ImagePreviewModal 
                isOpen={!!previewUrl} 
                imageUrl={previewUrl} 
                onClose={() => setPreviewUrl(null)} 
            />
            {/* Column 1: Index */}
            <div className="flex flex-col items-center gap-2 pt-1">
                <span className="text-xs font-mono text-gray-500 bg-dark-900 px-1.5 py-0.5 rounded-full min-w-[24px] text-center">{index + 1}</span>
                <input type="checkbox" className="rounded bg-dark-700 border-dark-600 w-4 h-4 cursor-pointer accent-accent"/>
            </div>

            {/* Column 2: Script */}
            <div className="space-y-3">
                 <div className="relative">
                     <div className="flex justify-between items-center mb-1">
                       <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">视觉描述 (Prompt)</label>
                       <span className="text-[10px] text-dark-600 cursor-pointer hover:text-accent">AI 优化</span>
                    </div>
                    <textarea 
                        className="w-full bg-dark-900/50 border border-dark-700 rounded p-2 text-sm text-gray-300 focus:border-accent focus:outline-none resize-none h-20 placeholder-gray-700 transition-colors"
                        value={shot.prompt}
                        placeholder="描述画面内容、镜头角度、光影..."
                        onChange={(e) => onUpdate(shot.id, { ...shot, prompt: e.target.value })}
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
                                onClick={() => onCharacterClick && onCharacterClick(charId)}
                                title={char?.name || "未知角色"}
                            >
                                <img src={avatarUrl} className="w-full h-full object-cover" alt="character"/>
                                <div className="absolute inset-0 bg-black/60 hidden group-hover/char:flex items-center justify-center">
                                    <span className="text-[8px] text-white">换图</span>
                                </div>
                                <button
                                    className="absolute top-0 right-0 p-0.5 bg-black/50 rounded-bl hidden group-hover/char:block"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        if (confirm(`确定移除 ${char?.name || '该角色'} 出场吗？`)) {
                                            const newCharacters = (shot.characters || []).filter(id => id !== charId);
                                            onUpdate && onUpdate(shot.id, { ...shot, characters: newCharacters });
                                        }
                                    }}
                                    title="移除角色"
                                >
                                    <Trash2 size={10} className="text-red-400"/>
                                </button>
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
                                        onUpdate(shot.id, { ...shot, characters: [...shot.characters, newCharId] });
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

            {/* Column 4: Scene (Reference) */}
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
                                        onUpdate(shot.id, { ...shot, scene_id: nextId });
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
                 
                 {/* Scene Asset Info */}
                 {shot.scene_id && allScenes ? (
                     <div 
                        className="aspect-video w-full rounded overflow-hidden border border-dark-700 relative group/scene cursor-pointer"
                        onClick={() => onSceneClick && onSceneClick(shot.scene_id)}
                        title="点击更换场景图片"
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
                        
                        {/* Hover Overlay */}
                        <div className="absolute inset-0 bg-black/50 hidden group-hover/scene:flex items-center justify-center">
                            <span className="text-xs text-white">更换图片</span>
                        </div>

                        {/* Scene Name Badge */}
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
                            onChange={(e) => onUpdate(shot.id, { ...shot, scene_id: e.target.value })}
                            value=""
                        >
                            <option value="" disabled>选择场景...</option>
                            {allScenes?.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    </div>
                 )}
                 
                 {/* Scene Reference Toggle */}
                 {shot.scene_id && (
                     <div className="flex items-center gap-2 mt-1 px-1">
                        <input 
                            type="checkbox" 
                            id={`use-scene-ref-${shot.id}`}
                            checked={shot.use_scene_ref || false}
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
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">分镜</label>
                    <div className="flex items-center gap-1 text-[10px] text-dark-500">
                        {/* Panel Layout Selector */}
                        <select
                            value={shot.panel_layout || "3-panel"}
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
                        onClick={() => onShotImageClick && onShotImageClick(shot.id)}
                    >
                        <img src={shot.image_url} className="w-full h-full object-cover" alt="scene"/>
                        <div 
                            className="absolute inset-0 bg-black/50 hidden group-hover/image:flex items-center justify-center pointer-events-none" 
                        >
                            <span className="text-xs text-white">点击更换图片</span>
                        </div>
                        <button
                            className="absolute top-2 right-2 p-1.5 bg-black/50 hover:bg-black/70 text-white rounded hidden group-hover/image:block z-10"
                            onClick={(e) => {
                                e.stopPropagation();
                                setPreviewUrl(shot.image_url);
                            }}
                            title="放大查看"
                        >
                            <Maximize size={16} />
                        </button>
                    </div>
                ) : (
                    <div className="aspect-video w-full rounded border border-dashed border-dark-600 flex flex-col items-center justify-center gap-2 text-dark-500 bg-dark-900/30">
                        <Image size={20}/>
                        <span className="text-xs">暂无分镜，右侧输入数量后点击“生成”</span>
                    </div>
                 )}
                 {Array.isArray(shot.image_candidates) && shot.image_candidates.length > 1 && (
                    <div className="flex gap-2 overflow-x-auto pt-1">
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
                                </button>
                            );
                        })}
                    </div>
                 )}
            </div>

            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">视频</label>
                    {shot.video_url && (
                        <span
                            className="text-[10px] text-dark-500 cursor-pointer hover:text-accent"
                            onClick={() => onGenerate && onGenerate(shot.id, 'video')}
                        >
                            重生成
                        </span>
                    )}
                 </div>

                 {shot.video_url ? (
                     <div className="aspect-video w-full rounded overflow-hidden border border-dark-700 bg-black relative group/video">
                        <video src={shot.video_url} className="w-full h-full object-cover" controls />
                     </div>
                 ) : (
                    <div className="aspect-video w-full rounded border border-dashed border-dark-600 flex flex-col items-center justify-center gap-2 bg-dark-900/30 relative">
                        {shot.image_url ? (
                             <button 
                                onClick={() => onGenerate(shot.id, 'video')}
                                className="absolute inset-0 flex flex-col items-center justify-center gap-2 hover:bg-dark-700 text-dark-500 hover:text-accent hover:border-accent transition-colors rounded"
                            >
                                <Video size={20}/>
                                <span className="text-xs">生成视频</span>
                            </button>
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
