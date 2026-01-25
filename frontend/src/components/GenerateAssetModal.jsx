import React, { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';

const GenerateAssetModal = ({ isOpen, onClose, onSubmit, type, initialName = "", initialPrompt = "" }) => {
    const [prompt, setPrompt] = useState('');
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setName(initialName);
            setPrompt(initialPrompt || '');
        }
    }, [isOpen, initialName, initialPrompt]);

    if (!isOpen) return null;

    const handleSubmit = async () => {
        if (!prompt.trim() || !name.trim()) return;
        setLoading(true);
        try {
            await onSubmit(name, prompt, type);
            onClose();
            setPrompt('');
            setName('');
        } catch (e) {
            console.error(e);
            alert("生成失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-dark-800 border border-dark-700 rounded-lg w-[500px] flex flex-col shadow-2xl">
                <div className="flex justify-between items-center p-4 border-b border-dark-700">
                    <h2 className="text-gray-200 font-medium">
                        {initialName ? `重新生成${type === 'character' ? '角色' : '场景'}` : (type === 'character' ? '生成角色' : '生成场景')}
                    </h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-white">
                        <X size={18} />
                    </button>
                </div>
                
                <div className="p-4 space-y-4">
                    <div>
                        <label className="block text-xs text-gray-500 mb-1 uppercase">名称</label>
                        <input 
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder={type === 'character' ? "角色名称 (如: 陈远)" : "场景名称 (如: 外门练武场)"}
                            className={`w-full bg-dark-900 text-gray-200 text-sm p-3 rounded border border-dark-700 outline-none focus:border-accent ${initialName ? 'opacity-50 cursor-not-allowed' : ''}`}
                            disabled={!!initialName}
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-500 mb-1 uppercase">提示词 (Prompt)</label>
                        <textarea 
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="描述画面细节..."
                            className="w-full h-32 bg-dark-900 text-gray-200 text-sm p-3 rounded border border-dark-700 outline-none focus:border-accent resize-none"
                        />
                    </div>
                </div>

                <div className="p-4 border-t border-dark-700 flex justify-end gap-2">
                    <button 
                        onClick={onClose}
                        className="px-4 py-2 rounded text-sm text-gray-400 hover:text-white hover:bg-dark-700 transition-colors"
                    >
                        取消
                    </button>
                    <button 
                        onClick={handleSubmit}
                        disabled={loading || !prompt.trim() || !name.trim()}
                        className="px-6 py-2 rounded text-sm bg-accent text-white font-medium hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {loading && <Loader2 size={14} className="animate-spin" />}
                        {loading ? '生成中...' : '开始生成'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default GenerateAssetModal;
