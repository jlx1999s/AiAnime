import React from 'react';
import { Plus, Trash2, Image, Play, Video, MoveUp, MoveDown } from 'lucide-react';

const ShotItem = ({ shot, index, onDelete, onUpdate, onGenerate }) => {
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
                    {shot.characters.map((charId, i) => (
                        <div key={i} className="aspect-square rounded bg-dark-700 border border-dark-600 overflow-hidden relative group/char">
                            <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${charId}`} className="w-full h-full object-cover" alt="character"/>
                            <div className="absolute inset-0 bg-black/60 hidden group-hover/char:flex items-center justify-center cursor-pointer">
                                <Trash2 size={10} className="text-red-400"/>
                            </div>
                        </div>
                    ))}
                    <button className="aspect-square rounded border border-dashed border-dark-600 flex items-center justify-center hover:bg-dark-700 text-dark-500 hover:text-accent hover:border-accent transition-colors">
                        <Plus size={14}/>
                    </button>
                 </div>
            </div>

            {/* Column 4: Scene */}
            <div className="space-y-2">
                 <div className="flex justify-between items-center">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">场景</label>
                    <Plus size={12} className="cursor-pointer hover:text-white text-gray-500"/>
                 </div>
                 <div className="aspect-video w-full rounded border border-dashed border-dark-600 flex items-center justify-center hover:bg-dark-700 text-dark-500 hover:text-accent hover:border-accent transition-colors cursor-pointer bg-dark-900/30">
                    <div className="flex flex-col items-center gap-1">
                        <Image size={16}/>
                        <span className="text-[10px]">选择场景</span>
                    </div>
                 </div>
            </div>

            {/* Column 5: Video */}
            <div className="flex flex-col gap-2">
                 <div className="relative group/preview aspect-video bg-black rounded overflow-hidden border border-dark-700">
                    <img src={shot.image_url || shot.preview} className="w-full h-full object-cover opacity-80 group-hover/preview:opacity-100 transition-opacity" alt="preview"/>
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover/preview:opacity-100 transition-opacity bg-black/40">
                        <button className="p-2 bg-accent rounded-full text-white hover:scale-110 transition-transform shadow-lg">
                            <Play size={20} fill="currentColor"/>
                        </button>
                    </div>
                    <span className="absolute top-1 right-1 bg-black/60 text-[10px] px-1 rounded text-white backdrop-blur-sm">Shot {index + 1}</span>
                 </div>
                 <div className="grid grid-cols-2 gap-2">
                    <button 
                        onClick={() => onGenerate(shot.id, 'image')}
                        className="flex items-center justify-center gap-1 bg-dark-700 hover:bg-dark-600 py-1.5 rounded text-xs text-gray-300 transition-colors"
                    >
                        <Image size={12}/> 生成图片
                    </button>
                    <button 
                        onClick={() => onGenerate(shot.id, 'video')}
                        className="flex items-center justify-center gap-1 bg-dark-700 hover:bg-dark-600 py-1.5 rounded text-xs text-gray-300 transition-colors"
                    >
                        <Video size={12}/> 生成视频
                    </button>
                 </div>
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
