import React, { useState } from 'react';
import { Film, Plus } from 'lucide-react';

const AddScriptModal = ({ isOpen, onClose, onSubmit }) => {
    const [content, setContent] = useState("");
    const [isParsing, setIsParsing] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async () => {
        if (!content.trim()) return;
        setIsParsing(true);
        await onSubmit(content);
        setIsParsing(false);
        setContent("");
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="bg-dark-800 w-[600px] rounded-lg border border-dark-700 shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
                <div className="p-4 border-b border-dark-700 flex justify-between items-center bg-dark-900">
                    <h3 className="font-bold text-gray-200 flex items-center gap-2">
                        <Film size={18} className="text-accent"/> 
                        添加剧本 (AI 自动解析)
                    </h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-white"><Plus size={20} className="rotate-45"/></button>
                </div>
                <div className="p-4 flex-1 flex flex-col gap-4">
                    <div className="bg-blue-500/10 border border-blue-500/20 rounded p-3 text-xs text-blue-200">
                        💡 粘贴小说、剧本片段，AI 将自动拆分为分镜镜头。建议包含场景描述、动作和台词。
                    </div>
                    <textarea 
                        className="flex-1 w-full bg-dark-900 border border-dark-700 rounded p-3 text-sm text-gray-300 focus:border-accent focus:outline-none resize-none min-h-[300px]"
                        placeholder="例如：
场景：幽暗的森林
1. 陆远气喘吁吁地奔跑，回头张望。（特写）
2. 前方出现一道悬崖。（远景）
..."
                        value={content}
                        onChange={e => setContent(e.target.value)}
                    />
                </div>
                <div className="p-4 border-t border-dark-700 bg-dark-900 flex justify-end gap-3">
                    <button onClick={onClose} className="px-4 py-2 rounded text-sm text-gray-400 hover:text-white hover:bg-dark-700">取消</button>
                    <button 
                        onClick={handleSubmit} 
                        disabled={isParsing || !content.trim()}
                        className="px-6 py-2 rounded text-sm bg-accent text-white font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {isParsing ? '正在解析...' : '开始智能拆解'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AddScriptModal;
