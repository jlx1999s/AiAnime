import React from 'react';
import { Plus, Trash2, Image, Play, Video, MoveUp, MoveDown } from 'lucide-react';

const ShotItem = ({ shot, index, onDelete, onUpdate, onGenerate, allCharacters, onCharacterClick, allScenes, onSceneClick, onShotImageClick }) => {
    return (
        <div className="grid grid-cols-[40px_minmax(300px,2fr)_1fr_1fr_1.5fr_40px] gap-4 p-4 border-b border-dark-700 bg-dark-800/30 hover:bg-dark-800 transition-colors group items-start">
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
                    <Plus size={12} className="cursor-pointer hover:text-white text-gray-500"/>
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
                            </div>
                        );
                    })}
                    <button className="aspect-square rounded border border-dashed border-dark-600 flex items-center justify-center hover:bg-dark-700 text-dark-500 hover:text-accent hover:border-accent transition-colors">
                        <Plus size={14}/>
                    </button>
                 </div>
            </div>

            {/* Column 4: Scene (Image Generation) */}
            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">场景 (图片)</label>
                    {shot.image_url && <span className="text-[10px] text-dark-500 cursor-pointer hover:text-accent" onClick={() => onGenerate(shot.id, 'image')}>重绘</span>}
                 </div>
                 
                 {/* Scene Asset Info */}
                 {shot.scene_id && allScenes && (
                     <div 
                        className="flex items-center gap-2 p-1 bg-dark-900 rounded border border-dark-700 cursor-pointer hover:border-accent group/scene"
                        onClick={() => onSceneClick && onSceneClick(shot.scene_id)}
                        title="点击上传/更换场景参考图"
                     >
                         <div className="w-8 h-8 rounded bg-dark-800 flex-shrink-0 overflow-hidden border border-dark-600">
                             {(() => {
                                 const scene = allScenes.find(s => s.id === shot.scene_id);
                                 return scene?.image_url ? (
                                     <img src={scene.image_url} className="w-full h-full object-cover" alt="scene ref" />
                                 ) : (
                                     <div className="w-full h-full flex items-center justify-center text-dark-500">
                                         <Image size={12}/>
                                     </div>
                                 );
                             })()}
                         </div>
                         <div className="flex-1 min-w-0">
                             <div className="text-[10px] text-gray-300 truncate font-medium">
                                 {allScenes.find(s => s.id === shot.scene_id)?.name || "未知场景"}
                             </div>
                             <div className="text-[8px] text-gray-500 truncate group-hover/scene:text-accent">
                                 点击上传参考图
                             </div>
                         </div>
                     </div>
                 )}

                 {shot.image_url ? (
                    <div 
                        className="aspect-video w-full rounded overflow-hidden border border-dark-700 relative group/image cursor-pointer"
                        onClick={() => onShotImageClick && onShotImageClick(shot.id)}
                    >
                        <img src={shot.image_url} className="w-full h-full object-cover" alt="scene"/>
                        <div 
                            className="absolute inset-0 bg-black/50 hidden group-hover/image:flex items-center justify-center" 
                        >
                            <span className="text-xs text-white">点击更换图片</span>
                        </div>
                    </div>
                ) : (
                    <button 
                        onClick={() => onGenerate(shot.id, 'image')}
                        className="aspect-video w-full rounded border border-dashed border-dark-600 flex flex-col items-center justify-center gap-2 hover:bg-dark-700 text-dark-500 hover:text-accent hover:border-accent transition-colors bg-dark-900/30"
                    >
                        <Image size={20}/>
                        <span className="text-xs">生成图片</span>
                    </button>
                 )}
            </div>

            {/* Column 5: Video (Video Generation) */}
            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">视频</label>
                    {shot.video_url && <span className="text-[10px] text-dark-500 cursor-pointer hover:text-accent" onClick={() => onGenerate(shot.id, 'video')}>重生成</span>}
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
                <button className="hover:text-white hover:bg-dark-700 p-1 rounded text-gray-500" title="上移"><MoveUp size={14}/></button>
                <button className="hover:text-white hover:bg-dark-700 p-1 rounded text-gray-500" title="下移"><MoveDown size={14}/></button>
                <button className="hover:text-red-400 hover:bg-dark-700 p-1 rounded mt-2 text-gray-500" onClick={() => onDelete(shot.id)} title="删除"><Trash2 size={14}/></button>
            </div>
        </div>
    );
};

export default ShotItem;
