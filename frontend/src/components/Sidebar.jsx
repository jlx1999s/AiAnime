import React, { useState } from 'react';
import { Trash2, Search, Plus, Wand2, RefreshCw, Maximize } from 'lucide-react';
import ImagePreviewModal from './ImagePreviewModal';

const Sidebar = ({ characters, scenes, onSceneClick, onCharacterClick, onAddCharacter, onAddScene, onGenerateCharacter, onGenerateScene, onDeleteCharacter, onRegenerateCharacter, onRegenerateScene, onGenerateAllCharacters, onGenerateAllScenes, isGeneratingCharacters, isGeneratingScenes, defaultSceneId, onSetDefaultScene }) => {
    const [activeTab, setActiveTab] = useState('chars');
    const [previewUrl, setPreviewUrl] = useState(null);

    return (
        <aside className="w-80 border-l border-dark-700 bg-dark-800 flex flex-col flex-shrink-0">
            <ImagePreviewModal 
                isOpen={!!previewUrl} 
                imageUrl={previewUrl} 
                onClose={() => setPreviewUrl(null)} 
            />
            <div className="flex border-b border-dark-700">
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${activeTab === 'chars' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setActiveTab('chars')}
                >角色资产</button>
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${activeTab === 'scenes' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setActiveTab('scenes')}
                >场景资产</button>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
                {activeTab === 'chars' && (
                    <div className="space-y-6">
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <h3 className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                                    角色列表 ({characters?.length || 0})
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
                                    <div className="relative">
                                        <input type="text" placeholder="搜索..." className="bg-dark-900 text-xs px-2 py-1 pl-6 rounded w-24 border border-dark-700 focus:border-accent outline-none"/>
                                        <Search size={10} className="absolute left-1.5 top-1.5 text-gray-500"/>
                                    </div>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                {characters?.map(char => (
                                    <div 
                                        key={char.id} 
                                        className="flex flex-col items-center gap-1 group cursor-pointer"
                                        onClick={() => onCharacterClick && onCharacterClick(char.id)}
                                    >
                                        <div className="w-16 h-16 rounded overflow-hidden bg-dark-600 border border-transparent group-hover:border-accent relative">
                                            <img src={char.avatar_url || char.avatar} alt={char.name} className="w-full h-full object-cover"/>
                                            <div className="absolute top-0 right-0 hidden group-hover:flex">
                                                <button 
                                                    className="p-0.5 bg-black/50 hover:bg-black/70 text-white"
                                                    onClick={(e) => { e.stopPropagation(); setPreviewUrl(char.avatar_url || char.avatar); }}
                                                    title="放大查看"
                                                >
                                                    <Maximize size={10} />
                                                </button>
                                                <button 
                                                    className="p-0.5 bg-black/50 hover:bg-black/70 text-white"
                                                    onClick={(e) => { e.stopPropagation(); onRegenerateCharacter && onRegenerateCharacter(char); }}
                                                    title="重新生成图片"
                                                >
                                                    <RefreshCw size={10} />
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
                                ))}
                                
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
                {activeTab === 'scenes' && (
                     <div className="space-y-6">
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <h3 className="text-xs font-bold text-gray-500 uppercase flex items-center gap-2">
                                    场景列表 ({scenes?.length || 0})
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
                                    <div className="relative">
                                        <input type="text" placeholder="搜索..." className="bg-dark-900 text-xs px-2 py-1 pl-6 rounded w-24 border border-dark-700 focus:border-accent outline-none"/>
                                        <Search size={10} className="absolute left-1.5 top-1.5 text-gray-500"/>
                                    </div>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                {scenes?.map(scene => (
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
                                                    className="p-1 bg-black/50 hover:bg-black/70 text-white rounded"
                                                    onClick={(e) => { e.stopPropagation(); onRegenerateScene && onRegenerateScene(scene); }}
                                                    title="重新生成图片"
                                                >
                                                    <RefreshCw size={12} />
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
                                ))}

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
            </div>
        </aside>
    );
};

export default Sidebar;
