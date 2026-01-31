import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Wand2, RefreshCw, Maximize, Save, Image as ImageIcon, Film } from 'lucide-react';
import { ApiService } from '../services/api';
import ImagePreviewModal from '../components/ImagePreviewModal';

const AssetManager = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);
    const [activeTab, setActiveTab] = useState('characters'); // 'characters' or 'scenes'
    const [loading, setLoading] = useState(true);
    const [previewUrl, setPreviewUrl] = useState(null);
    const [generatingId, setGeneratingId] = useState(null);
    const importMdRef = React.useRef(null);
    const [isBulkGeneratingChars, setIsBulkGeneratingChars] = useState(false);
    const [isBulkGeneratingScenes, setIsBulkGeneratingScenes] = useState(false);

    useEffect(() => {
        loadProject();
    }, [projectId]);

    const loadProject = async () => {
        setLoading(true);
        try {
            const data = await ApiService.getProject(projectId);
            setProject(data);
        } catch (error) {
            console.error("Failed to load project", error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateAsset = async (type, assetId, updates) => {
        if (!project) return;
        
        const listKey = type === 'character' ? 'characters' : 'scenes';
        const updatedList = project[listKey].map(item => 
            item.id === assetId ? { ...item, ...updates } : item
        );
        
        // Optimistic update
        setProject(prev => ({ ...prev, [listKey]: updatedList }));

        try {
            await ApiService.updateProject(projectId, { [listKey]: updatedList });
        } catch (error) {
            console.error(`Failed to update ${type}`, error);
            loadProject(); // Revert on error
        }
    };

    const handleDeleteAsset = async (type, assetId) => {
        if (!confirm('确定要删除这个资产吗？')) return;
        
        const listKey = type === 'character' ? 'characters' : 'scenes';
        const updatedList = project[listKey].filter(item => item.id !== assetId);
        
        setProject(prev => ({ ...prev, [listKey]: updatedList }));

        try {
            await ApiService.updateProject(projectId, { [listKey]: updatedList });
        } catch (error) {
            console.error(`Failed to delete ${type}`, error);
            loadProject();
        }
    };

    const handleGenerateAsset = async (type, asset) => {
        if (generatingId) return;
        setGeneratingId(asset.id);

        try {
            const prompt = `${asset.name}, ${asset.prompt || ''}, high quality`;
            const result = await ApiService.generateAsset(prompt, type, projectId);
            
            const updated = type === 'character' ? { avatar_url: result.url } : { image_url: result.url };
            const listKey = type === 'character' ? 'characters' : 'scenes';
            
            // Optimistic update
            const updatedList = project[listKey].map(item => 
                item.id === asset.id ? { ...item, ...updated } : item
            );
            setProject(prev => ({ ...prev, [listKey]: updatedList }));
            
            if (type === 'character') {
                 await ApiService.updateCharacter(projectId, asset.id, { ...asset, ...updated });
            } else {
                 await ApiService.updateScene(projectId, asset.id, { ...asset, ...updated });
            }
            
        } catch (error) {
            console.error("Generation failed", error);
            alert("生成失败: " + (error.message || error));
        } finally {
            setGeneratingId(null);
        }
    };

    if (loading) return <div className="h-screen flex items-center justify-center bg-dark-900 text-white">加载中...</div>;
    if (!project) return <div className="h-screen flex items-center justify-center bg-dark-900 text-white">项目未找到</div>;

    const assets = activeTab === 'characters' ? project.characters : project.scenes;

    return (
        <div className="min-h-screen bg-dark-900 text-gray-200 flex flex-col">
            <ImagePreviewModal 
                isOpen={!!previewUrl} 
                imageUrl={previewUrl} 
                onClose={() => setPreviewUrl(null)} 
            />
            
            {/* Header */}
            <header className="h-14 border-b border-dark-700 bg-dark-800 flex items-center justify-between px-6 sticky top-0 z-10">
                <div className="flex items-center gap-4">
                    <button 
                        onClick={() => navigate(`/project/${projectId}`)}
                        className="p-2 hover:bg-dark-700 rounded-full transition-colors text-gray-400 hover:text-white"
                        title="返回编辑器"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-lg font-bold text-white">
                        资产管理 <span className="text-gray-500 text-sm font-normal">| {project.name}</span>
                    </h1>
                </div>
                <div className="flex bg-dark-900 rounded p-1">
                    <button 
                        className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === 'characters' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'}`}
                        onClick={() => setActiveTab('characters')}
                    >
                        角色 ({project.characters?.length || 0})
                    </button>
                    <button 
                        className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === 'scenes' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'}`}
                        onClick={() => setActiveTab('scenes')}
                    >
                        场景 ({project.scenes?.length || 0})
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${isBulkGeneratingChars ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-accent text-white hover:brightness-110'}`}
                        disabled={isBulkGeneratingChars || !!generatingId}
                        onClick={async () => {
                            if (!project) return;
                            const targets = (project.characters || []).filter(c => !c.avatar_url || c.avatar_url.includes('dicebear'));
                            if (targets.length === 0) {
                                alert('没有需要生成的角色');
                                return;
                            }
                            if (!confirm(`确定要为 ${targets.length} 个角色生成图片吗？`)) return;
                            setIsBulkGeneratingChars(true);
                            const style = project?.style || 'anime';
                            try {
                                for (const char of targets) {
                                    try {
                                        const prompt = `${char.name}, ${char.prompt || char.description || 'character portrait'}, ${style} style, high quality`;
                                        const result = await ApiService.generateAsset(prompt, 'character', projectId);
                                        const updated = { avatar_url: result.url };
                                        setProject(prev => ({ ...prev, characters: (prev.characters || []).map(c => c.id === char.id ? { ...c, ...updated } : c) }));
                                        await ApiService.updateCharacter(projectId, char.id, { ...char, ...updated });
                                    } catch (e) {}
                                }
                            } finally {
                                setIsBulkGeneratingChars(false);
                            }
                        }}
                    >
                        角色一键生成
                    </button>
                    <button
                        className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${isBulkGeneratingScenes ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-accent text-white hover:brightness-110'}`}
                        disabled={isBulkGeneratingScenes || !!generatingId}
                        onClick={async () => {
                            if (!project) return;
                            const targets = (project.scenes || []).filter(s => !s.image_url);
                            if (targets.length === 0) {
                                alert('没有需要生成的场景');
                                return;
                            }
                            if (!confirm(`确定要为 ${targets.length} 个场景生成图片吗？`)) return;
                            setIsBulkGeneratingScenes(true);
                            const style = project?.style || 'anime';
                            try {
                                for (const scene of targets) {
                                    try {
                                        const prompt = `${scene.name}, ${scene.prompt || scene.description || 'scenery'}, ${style} style, high quality`;
                                        const result = await ApiService.generateAsset(prompt, 'scene', projectId);
                                        const updated = { image_url: result.url };
                                        setProject(prev => ({ ...prev, scenes: (prev.scenes || []).map(s => s.id === scene.id ? { ...s, ...updated } : s) }));
                                        await ApiService.updateScene(projectId, scene.id, { ...scene, ...updated });
                                    } catch (e) {}
                                }
                            } finally {
                                setIsBulkGeneratingScenes(false);
                            }
                        }}
                    >
                        场景一键生成
                    </button>
                    <button
                        className="p-2 hover:bg-dark-700 rounded-full transition-colors text-gray-400 hover:text-white"
                        title={activeTab === 'characters' ? '导入角色MD' : '导入场景MD'}
                        onClick={() => importMdRef.current?.click()}
                    >
                        <Save size={18} />
                    </button>
                    <input
                        type="file"
                        ref={importMdRef}
                        className="hidden"
                        accept=".md"
                        onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            try {
                                if (activeTab === 'characters') {
                                    const res = await ApiService.importCharactersFromMd(projectId, file);
                                    const added = res.characters || [];
                                    if (added.length) {
                                        setProject(prev => ({ ...prev, characters: [...(prev.characters || []), ...added] }));
                                        alert(`成功导入 ${added.length} 个角色`);
                                    } else {
                                        alert('未解析到有效角色数据');
                                    }
                                } else {
                                    const res = await ApiService.importScenesFromMd(projectId, file);
                                    const added = res.scenes || [];
                                    if (added.length) {
                                        setProject(prev => ({ ...prev, scenes: [...(prev.scenes || []), ...added] }));
                                        alert(`成功导入 ${added.length} 个场景`);
                                    } else {
                                        alert('未解析到有效场景数据');
                                    }
                                }
                            } catch (err) {
                                console.error('Import MD failed', err);
                                alert('导入失败');
                            }
                            e.target.value = null;
                        }}
                    />
                </div>
            </header>

            {/* Content */}
            <main className="flex-1 p-6 overflow-y-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
                    {/* Add New Card */}
                    <div 
                        className="bg-dark-800 border-2 border-dashed border-dark-600 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-accent hover:bg-dark-700 transition-colors group h-56"
                        onClick={async () => {
                            const name = prompt(`请输入新${activeTab === 'characters' ? '角色' : '场景'}名称`);
                            if (name) {
                                const newAsset = {
                                    id: `${activeTab === 'characters' ? 'char' : 'scene'}_${Date.now()}`,
                                    name,
                                    prompt: '',
                                    [activeTab === 'characters' ? 'avatar' : 'image_url']: ''
                                };
                                const listKey = activeTab === 'characters' ? 'characters' : 'scenes';
                                const newList = [...(project[listKey] || []), newAsset];
                                handleUpdateAsset(activeTab === 'characters' ? 'character' : 'scene', newAsset.id, {}); // Just to trigger update with new list
                                // Actually handleUpdateAsset updates a specific item. We need to update the list.
                                setProject(prev => ({ ...prev, [listKey]: newList }));
                                await ApiService.updateProject(projectId, { [listKey]: newList });
                            }
                        }}
                    >
                        <Plus size={48} className="text-dark-600 group-hover:text-accent mb-2" />
                        <span className="text-gray-500 font-medium group-hover:text-accent">
                            新建{activeTab === 'characters' ? '角色' : '场景'}
                        </span>
                    </div>

                    {/* Asset Cards */}
                    {assets?.map(asset => (
                        <div key={asset.id} className="bg-dark-800 rounded-lg overflow-hidden border border-dark-700 shadow-lg flex flex-col">
                            {/* Image Area */}
                            <div className="relative bg-dark-900 group h-56">
                                <img 
                                    src={asset.avatar_url || asset.avatar || asset.image_url} 
                                    alt={asset.name} 
                                    className="w-full h-full object-contain"
                                    onError={(e) => { e.target.src = 'https://placehold.co/600x400/1a1b1e/FFF?text=No+Image'; }}
                                />
                                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                    <button 
                                        className="p-2 bg-dark-700 rounded-full hover:bg-accent text-white transition-colors"
                                        onClick={() => setPreviewUrl(asset.avatar_url || asset.avatar || asset.image_url)}
                                        title="预览"
                                    >
                                        <Maximize size={18} />
                                    </button>
                                    <button 
                                        className={`p-2 bg-dark-700 rounded-full hover:bg-accent text-white transition-colors ${generatingId === asset.id ? 'animate-spin' : ''}`}
                                        onClick={() => handleGenerateAsset(activeTab === 'characters' ? 'character' : 'scene', asset)}
                                        title="重新生成"
                                        disabled={generatingId === asset.id || (activeTab === 'characters' ? isBulkGeneratingChars : isBulkGeneratingScenes)}
                                    >
                                        {generatingId === asset.id ? <RefreshCw size={18} /> : <Wand2 size={18} />}
                                    </button>
                                    <button 
                                        className="p-2 bg-red-900/80 hover:bg-red-600 rounded-full text-white transition-colors"
                                        onClick={() => handleDeleteAsset(activeTab === 'characters' ? 'character' : 'scene', asset.id)}
                                        title="删除"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            </div>

                            {/* Info Area */}
                            <div className="p-3 flex-1 flex flex-col gap-2">
                                <div>
                                    <label className="text-[10px] uppercase text-gray-500 font-bold mb-1 block">名称</label>
                                    <input 
                                        type="text" 
                                        value={asset.name}
                                        onChange={(e) => handleUpdateAsset(activeTab === 'characters' ? 'character' : 'scene', asset.id, { name: e.target.value })}
                                        className="w-full bg-dark-900 border border-dark-700 rounded px-2 py-1 text-sm text-white focus:border-accent outline-none"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label className="text-[10px] uppercase text-gray-500 font-bold mb-1 block">
                                        视觉描述 (Prompt)
                                    </label>
                                    <textarea 
                                        value={asset.prompt || ''}
                                        onChange={(e) => handleUpdateAsset(activeTab === 'characters' ? 'character' : 'scene', asset.id, { prompt: e.target.value })}
                                        className="w-full h-20 bg-dark-900 border border-dark-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-accent outline-none resize-none"
                                        placeholder="输入外观描述..."
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
};

export default AssetManager;
