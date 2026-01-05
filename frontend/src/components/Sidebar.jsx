import React, { useState } from 'react';
import { Film, Trash2, Search, User, Plus } from 'lucide-react';

const Sidebar = ({ characters, scenes, onSceneClick }) => {
    const [activeTab, setActiveTab] = useState('chars');

    return (
        <aside className="w-80 border-l border-dark-700 bg-dark-800 flex flex-col flex-shrink-0">
            <div className="flex border-b border-dark-700">
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${activeTab === 'chars' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setActiveTab('chars')}
                >角色</button>
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${activeTab === 'scenes' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setActiveTab('scenes')}
                >场景</button>
                <button 
                    className={`flex-1 py-3 text-sm font-medium ${activeTab === 'props' ? 'text-accent border-b-2 border-accent' : 'text-gray-400'}`}
                    onClick={() => setActiveTab('props')}
                >道具</button>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
                <button className="w-full bg-accent hover:bg-blue-600 text-white py-2 rounded mb-4 text-sm font-medium flex items-center justify-center gap-2">
                    <Film size={16}/> 批量生成
                </button>

                {activeTab === 'chars' && (
                    <div className="space-y-6">
                        <div>
                            <h3 className="text-xs font-bold text-gray-500 mb-3 uppercase flex items-center justify-between">
                                作品中角色 ({characters?.length || 0})
                                <span className="text-[10px] bg-dark-700 px-1 rounded">Active</span>
                            </h3>
                            <div className="grid grid-cols-3 gap-2">
                                {characters?.map(char => (
                                    <div key={char.id} className="flex flex-col items-center gap-1 group cursor-pointer">
                                        <div className="w-16 h-16 rounded overflow-hidden bg-dark-600 border border-transparent group-hover:border-accent relative">
                                            <img src={char.avatar_url || char.avatar} alt={char.name} className="w-full h-full object-cover"/>
                                            <div className="absolute top-0 right-0 p-0.5 bg-black/50 rounded-bl hidden group-hover:block">
                                                <Trash2 size={10} className="text-red-400"/>
                                            </div>
                                        </div>
                                        <span className="text-[10px] text-gray-400 truncate w-full text-center">{char.name}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <h3 className="text-xs font-bold text-gray-500 uppercase">全部可选角色</h3>
                                <div className="relative">
                                    <input type="text" placeholder="搜索..." className="bg-dark-900 text-xs px-2 py-1 pl-6 rounded w-24 border border-dark-700 focus:border-accent outline-none"/>
                                    <Search size={10} className="absolute left-1.5 top-1.5 text-gray-500"/>
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                {/* Mock Library */}
                                {[1,2,3,4,5,6].map(i => (
                                     <div key={i} className="flex flex-col items-center gap-1 group cursor-pointer opacity-60 hover:opacity-100 transition-opacity">
                                        <div className="w-16 h-16 rounded bg-dark-700 flex items-center justify-center border border-transparent group-hover:border-gray-500">
                                            <User size={24} className="text-dark-500"/>
                                        </div>
                                        <span className="text-[10px] text-gray-400">角色 {i}</span>
                                    </div>
                                ))}
                                <div className="flex flex-col items-center gap-1 cursor-pointer hover:text-accent group">
                                    <div className="w-16 h-16 rounded border border-dashed border-dark-600 flex items-center justify-center group-hover:border-accent group-hover:bg-dark-700">
                                        <Plus size={24}/>
                                    </div>
                                    <span className="text-[10px] text-gray-400 group-hover:text-accent">新建</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                {activeTab === 'scenes' && (
                     <div className="space-y-6">
                        <div>
                            <h3 className="text-xs font-bold text-gray-500 mb-3 uppercase flex items-center justify-between">
                                作品中场景 ({scenes?.length || 0})
                            </h3>
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
                                        </div>
                                        <span className="text-[10px] text-gray-400 truncate w-full">{scene.name}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                     </div>
                )}
            </div>
        </aside>
    );
};

export default Sidebar;
