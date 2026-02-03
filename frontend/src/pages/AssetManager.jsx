import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Wand2, RefreshCw, Maximize, Save, Image as ImageIcon, Film } from 'lucide-react';
import { ApiService } from '../services/api';
import ImagePreviewModal from '../components/ImagePreviewModal';

const AssetManager = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);
    const [activeTab, setActiveTab] = useState('characters'); // 'characters', 'scenes', 'shots', 'videos'
    const [loading, setLoading] = useState(true);
    const [previewUrl, setPreviewUrl] = useState(null);
    const [previewVideoUrl, setPreviewVideoUrl] = useState(null);
    const [generatingIds, setGeneratingIds] = useState(new Set());
    const importMdRef = React.useRef(null);
    const [isBulkGeneratingChars, setIsBulkGeneratingChars] = useState(false);
    const [isBulkGeneratingScenes, setIsBulkGeneratingScenes] = useState(false);
    const hasPendingAssets = (project?.characters || []).some((item) => item?.status === 'generating')
        || (project?.scenes || []).some((item) => item?.status === 'generating');
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    useEffect(() => {
        const user = ApiService.getCurrentUser();
        if (!user) {
            navigate('/');
            return;
        }
        loadProject();
    }, [projectId]);

    useEffect(() => {
        if (!projectId || !hasPendingAssets) return;
        const interval = setInterval(async () => {
            try {
                const data = await ApiService.getProject(projectId);
                setProject(data);
            } catch (error) {}
        }, 3000);
        return () => clearInterval(interval);
    }, [projectId, hasPendingAssets]);

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
        
        let listKey = 'characters';
        if (type === 'scene') listKey = 'scenes';
        if (type === 'shot') listKey = 'shots';

        const updatedList = project[listKey].map(item => 
            item.id === assetId ? { ...item, ...updates } : item
        );
        
        // Optimistic update
        setProject(prev => ({ ...prev, [listKey]: updatedList }));

        try {
            if (type === 'shot') {
                await ApiService.updateShot(projectId, assetId, updates);
            } else {
                await ApiService.updateProject(projectId, { [listKey]: updatedList });
            }
        } catch (error) {
            console.error(`Failed to update ${type}`, error);
            loadProject(); // Revert on error
        }
    };

    const handleDeleteAsset = async (type, assetId) => {
        if (!confirm('确定要删除这个资产吗？')) return;
        
        let listKey = 'characters';
        if (type === 'scene') listKey = 'scenes';
        if (type === 'shot') listKey = 'shots';

        const updatedList = project[listKey].filter(item => item.id !== assetId);
        
        setProject(prev => ({ ...prev, [listKey]: updatedList }));

        try {
            if (type === 'shot') {
                await ApiService.deleteShot(projectId, assetId);
            } else {
                await ApiService.updateProject(projectId, { [listKey]: updatedList });
            }
        } catch (error) {
            console.error(`Failed to delete ${type}`, error);
            loadProject();
        }
    };

    const getAssetPrompt = (asset) => {
        const prompt = asset?.prompt?.trim();
        if (prompt) return prompt;
        const name = asset?.name?.trim();
        return name || '';
    };

    const handleGenerateAsset = async (type, asset) => {
        const isBusy = generatingIds.has(asset.id) || asset?.status === 'generating';
        if (isBusy) return;
        setGeneratingIds(prev => {
            const next = new Set(prev);
            next.add(asset.id);
            return next;
        });

        try {
            const prompt = getAssetPrompt(asset);
            if (!prompt) {
                alert("请先填写名称或提示词");
                return;
            }
            const result = await ApiService.generateAsset(prompt, type, projectId, { asset_id: asset.id, name: asset.name });
            const listKey = type === 'character' ? 'characters' : 'scenes';
            if (result?.asset) {
                setProject(prev => {
                    const current = prev?.[listKey] || [];
                    const exists = current.some(item => item.id === result.asset.id);
                    const updatedList = exists
                        ? current.map(item => item.id === result.asset.id ? result.asset : item)
                        : [...current, result.asset];
                    return { ...prev, [listKey]: updatedList };
                });
            } else if (result?.url) {
                const updated = type === 'character' ? { avatar_url: result.url } : { image_url: result.url };
                setProject(prev => {
                    const current = prev?.[listKey] || [];
                    const updatedList = current.map(item =>
                        item.id === asset.id ? { ...item, ...updated } : item
                    );
                    return { ...prev, [listKey]: updatedList };
                });
                if (type === 'character') {
                    await ApiService.updateCharacter(projectId, asset.id, { ...asset, ...updated });
                } else {
                    await ApiService.updateScene(projectId, asset.id, { ...asset, ...updated });
                }
            }
            
        } catch (error) {
            console.error("Generation failed", error);
            alert("生成失败: " + (error.message || error));
        } finally {
            setGeneratingIds(prev => {
                const next = new Set(prev);
                next.delete(asset.id);
                return next;
            });
        }
    };

    if (loading) return <div className="h-screen flex items-center justify-center bg-dark-900 text-white">加载中...</div>;
    if (!project) return <div className="h-screen flex items-center justify-center bg-dark-900 text-white">项目未找到</div>;

    const assets = (() => {
        if (activeTab === 'characters') return project.characters;
        if (activeTab === 'scenes') return project.scenes;
        if (activeTab === 'shots') return project.shots;
        if (activeTab === 'videos') return (project.shots || []).filter(s => s.video_url);
        return [];
    })();

    const isReadOnlyTab = activeTab === 'shots' || activeTab === 'videos';

    return (
        <div className="min-h-screen bg-dark-900 text-gray-200 flex flex-col">
            <ImagePreviewModal 
                isOpen={!!previewUrl} 
                imageUrl={previewUrl} 
                onClose={() => setPreviewUrl(null)} 
            />
            {/* Simple Video Preview Modal */}
            {previewVideoUrl && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4" onClick={() => setPreviewVideoUrl(null)}>
                    <div className="relative max-w-5xl w-full max-h-screen bg-black rounded-lg overflow-hidden" onClick={e => e.stopPropagation()}>
                         <button 
                            className="absolute top-2 right-2 p-2 bg-dark-800/80 rounded-full hover:bg-dark-700 text-white z-10"
                            onClick={() => setPreviewVideoUrl(null)}
                        >
                            <ArrowLeft size={20} />
                        </button>
                        <video src={previewVideoUrl} controls autoPlay className="w-full h-full max-h-[80vh] object-contain" />
                    </div>
                </div>
            )}
            
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
                <div className="flex bg-dark-900 rounded p-1 gap-1">
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
                    <button 
                        className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === 'shots' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'}`}
                        onClick={() => setActiveTab('shots')}
                    >
                        分镜 ({project.shots?.length || 0})
                    </button>
                    <button 
                        className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === 'videos' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'}`}
                        onClick={() => setActiveTab('videos')}
                    >
                        视频 ({project.shots?.filter(s => s.video_url).length || 0})
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    {!isReadOnlyTab && (
                        <>
                            <button
                                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${isBulkGeneratingChars ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-accent text-white hover:brightness-110'}`}
                                disabled={isBulkGeneratingChars || generatingIds.size > 0}
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
                                        for (let i = 0; i < targets.length; i += 1) {
                                            const char = targets[i];
                                            try {
                                                const prompt = `${char.name}, ${char.prompt || char.description || 'character portrait'}, ${style} style, high quality`;
                                                const result = await ApiService.generateAsset(prompt, 'character', projectId, { asset_id: char.id, name: char.name });
                                                if (result?.asset) {
                                                    setProject(prev => ({ ...prev, characters: (prev.characters || []).map(c => c.id === result.asset.id ? result.asset : c) }));
                                                } else if (result?.url) {
                                                    const updated = { avatar_url: result.url };
                                                    setProject(prev => ({ ...prev, characters: (prev.characters || []).map(c => c.id === char.id ? { ...c, ...updated } : c) }));
                                                    await ApiService.updateCharacter(projectId, char.id, { ...char, ...updated });
                                                }
                                            } catch (e) {}
                                            if (i < targets.length - 1) {
                                                await sleep(3000);
                                            }
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
                                disabled={isBulkGeneratingScenes || generatingIds.size > 0}
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
                                        for (let i = 0; i < targets.length; i += 1) {
                                            const scene = targets[i];
                                            try {
                                                const prompt = `${scene.name}, ${scene.prompt || scene.description || 'scenery'}, ${style} style, high quality`;
                                                const result = await ApiService.generateAsset(prompt, 'scene', projectId, { asset_id: scene.id, name: scene.name });
                                                if (result?.asset) {
                                                    setProject(prev => ({ ...prev, scenes: (prev.scenes || []).map(s => s.id === result.asset.id ? result.asset : s) }));
                                                } else if (result?.url) {
                                                    const updated = { image_url: result.url };
                                                    setProject(prev => ({ ...prev, scenes: (prev.scenes || []).map(s => s.id === scene.id ? { ...s, ...updated } : s) }));
                                                    await ApiService.updateScene(projectId, scene.id, { ...scene, ...updated });
                                                }
                                            } catch (e) {}
                                            if (i < targets.length - 1) {
                                                await sleep(3000);
                                            }
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
                        </>
                    )}
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
                    {/* Add New Card - Only for Characters/Scenes */}
                    {!isReadOnlyTab && (
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
                    )}

                    {/* Asset Cards */}
                    {assets?.map(asset => {
                        const isVideoTab = activeTab === 'videos';
                        const imageUrl = activeTab === 'characters' ? asset.avatar_url || asset.avatar : asset.image_url;
                        const displayImage = isVideoTab ? (asset.image_url || 'https://placehold.co/600x400/1a1b1e/FFF?text=Video') : imageUrl;
                        
                        const isAssetGenerating = generatingIds.has(asset.id) || asset?.status === 'generating';
                        return (
                        <div key={asset.id} className="bg-dark-800 rounded-lg overflow-hidden border border-dark-700 shadow-lg flex flex-col">
                            {/* Image Area */}
                            <div className="relative bg-dark-900 group h-56">
                                <img 
                                    src={displayImage} 
                                    alt={asset.name || `Shot ${asset.order}`} 
                                    className="w-full h-full object-contain"
                                />
                                {isVideoTab && asset.video_url && (
                                     <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <div className="bg-black/50 rounded-full p-2">
                                            <Film size={24} className="text-white" />
                                        </div>
                                     </div>
                                )}
                                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                    <button 
                                        className="p-2 bg-dark-700 rounded-full hover:bg-accent text-white transition-colors"
                                        onClick={() => {
                                            if (isVideoTab && asset.video_url) {
                                                setPreviewVideoUrl(asset.video_url);
                                            } else {
                                                setPreviewUrl(displayImage);
                                            }
                                        }}
                                        title="预览"
                                    >
                                        <Maximize size={18} />
                                    </button>
                                    {!isReadOnlyTab && (
                                    <button 
                                        className={`p-2 bg-dark-700 rounded-full hover:bg-accent text-white transition-colors ${isAssetGenerating ? 'animate-spin' : ''}`}
                                        onClick={() => handleGenerateAsset(activeTab === 'characters' ? 'character' : 'scene', asset)}
                                        title="重新生成"
                                        disabled={isAssetGenerating || (activeTab === 'characters' ? isBulkGeneratingChars : isBulkGeneratingScenes)}
                                    >
                                        {isAssetGenerating ? <RefreshCw size={18} /> : <Wand2 size={18} />}
                                    </button>
                                    )}
                                    <button 
                                        className="p-2 bg-red-900/80 hover:bg-red-600 rounded-full text-white transition-colors"
                                        onClick={() => handleDeleteAsset(activeTab === 'characters' ? 'character' : (activeTab === 'scenes' ? 'scene' : 'shot'), asset.id)}
                                        title="删除"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            </div>

                            {/* Info Area */}
                            <div className="p-3 flex-1 flex flex-col gap-2">
                                <div>
                                    <label className="text-[10px] uppercase text-gray-500 font-bold mb-1 block">名称/序号</label>
                                    <input 
                                        type="text" 
                                        value={asset.name || (typeof asset.order === 'number' ? `Shot ${asset.order}` : 'Shot')}
                                        readOnly={isReadOnlyTab}
                                        onChange={(e) => !isReadOnlyTab && handleUpdateAsset(activeTab === 'characters' ? 'character' : 'scene', asset.id, { name: e.target.value })}
                                        className={`w-full bg-dark-900 border border-dark-700 rounded px-2 py-1 text-sm text-white focus:border-accent outline-none ${isReadOnlyTab ? 'cursor-default text-gray-400' : ''}`}
                                    />
                                </div>
                                <div className="flex-1">
                                    <label className="text-[10px] uppercase text-gray-500 font-bold mb-1 block">
                                        视觉描述 (Prompt)
                                    </label>
                                    <textarea 
                                        value={asset.prompt || ''}
                                        readOnly={isReadOnlyTab}
                                        onChange={(e) => !isReadOnlyTab && handleUpdateAsset(activeTab === 'characters' ? 'character' : 'scene', asset.id, { prompt: e.target.value })}
                                        className={`w-full h-20 bg-dark-900 border border-dark-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-accent outline-none resize-none ${isReadOnlyTab ? 'cursor-default' : ''}`}
                                        placeholder="输入外观描述..."
                                    />
                                </div>
                            </div>
                        </div>
                    )})}
                </div>
            </main>
        </div>
    );
};

export default AssetManager;
