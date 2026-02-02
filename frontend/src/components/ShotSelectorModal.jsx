import React from 'react';
import { X, Image } from 'lucide-react';

const ShotSelectorModal = ({ isOpen, onClose, onSelect, shots }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4" onClick={onClose}>
            <div 
                className="bg-dark-800 w-full max-w-4xl max-h-[80vh] rounded-lg shadow-2xl flex flex-col border border-dark-700"
                onClick={e => e.stopPropagation()}
            >
                <div className="flex justify-between items-center p-4 border-b border-dark-700">
                    <h3 className="text-lg font-bold text-gray-200">选择分镜图片</h3>
                    <button 
                        onClick={onClose}
                        className="p-1 hover:bg-dark-700 rounded-full text-gray-400 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                    <div className="grid grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3">
                        {shots.flatMap((shot, index) => {
                            const items = [];
                            
                            // 1. Custom Reference Image
                            if (shot.custom_image_url) {
                                items.push({
                                    key: `${shot.id}-custom`,
                                    url: shot.custom_image_url,
                                    label: `#${index + 1} 参考`,
                                    type: 'custom'
                                });
                            }

                            // 2. Shot Images (Candidates or Main)
                            if (Array.isArray(shot.image_candidates) && shot.image_candidates.length > 0) {
                                shot.image_candidates.forEach((url, cIdx) => {
                                    items.push({
                                        key: `${shot.id}-cand-${cIdx}`,
                                        url: url,
                                        label: `#${index + 1} 分镜-${cIdx + 1}`,
                                        type: 'shot'
                                    });
                                });
                            } else if (shot.image_url) {
                                items.push({
                                    key: `${shot.id}-main`,
                                    url: shot.image_url,
                                    label: `#${index + 1} 分镜`,
                                    type: 'shot'
                                });
                            }

                            return items;
                        }).map((item) => (
                            <div 
                                key={item.key}
                                className={`group relative aspect-video bg-dark-900 rounded border cursor-pointer hover:border-accent hover:ring-1 hover:ring-accent transition-all overflow-hidden ${item.type === 'custom' ? 'border-blue-900/50' : 'border-dark-700'}`}
                                onClick={() => onSelect(item.url)}
                            >
                                <img 
                                    src={item.url} 
                                    alt={item.label} 
                                    className="w-full h-full object-cover"
                                />
                                <div className={`absolute top-1 left-1 px-1.5 py-0.5 rounded text-[10px] text-white font-mono shadow-sm ${item.type === 'custom' ? 'bg-blue-600/80' : 'bg-black/60'}`}>
                                    {item.label}
                                </div>
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                            </div>
                        ))}
                        
                        {shots.every(s => !s.custom_image_url && !s.image_url && (!s.image_candidates || s.image_candidates.length === 0)) && (
                            <div className="col-span-full py-10 text-center text-gray-500 flex flex-col items-center gap-2">
                                <Image size={32} />
                                <p>没有可用的分镜图片</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShotSelectorModal;
