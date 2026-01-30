import React, { useState, useEffect } from 'react';
import { History, Settings, Image as ImageIcon } from 'lucide-react';
import { ApiService } from '../services/api';

const Header = ({ projects = [], currentProjectId, onChangeProject, onCreateProject, onRenameProject, onDeleteProject, onChangeStyle, onDuplicateProject, onExportProject, onImportProject, onOpenApiConfig, onOpenAssets }) => {
    const current = projects.find(p => p.id === currentProjectId);
    const [presets, setPresets] = useState([]);
    const [selectedPresets, setSelectedPresets] = useState({ text: '', image: '', video: '' });
    
    useEffect(() => {
        loadPresets();
    }, []);

    const loadPresets = async () => {
        try {
            const [presetsData, configData] = await Promise.all([
                ApiService.getApiPresets(),
                ApiService.getApiConfig()
            ]);
            
            const loadedPresets = presetsData || [];
            setPresets(loadedPresets);

            // Check active presets
            const newSelected = { text: '', image: '', video: '' };
            
            ['text', 'image', 'video'].forEach(type => {
                const typePresets = loadedPresets.filter(p => p.type === type);
                for (const preset of typePresets) {
                    // Check if all keys in preset.config match configData
                    // Only compare if preset has config keys
                    if (preset.config && Object.keys(preset.config).length > 0) {
                        const isMatch = Object.entries(preset.config).every(([key, value]) => {
                            return configData[key] === value;
                        });
                        if (isMatch) {
                            newSelected[type] = preset.name;
                            break; // Found the matching preset, take the first one
                        }
                    }
                }
            });
            
            setSelectedPresets(newSelected);

        } catch (e) {
            console.error("Failed to load presets or config", e);
        }
    };

    const handleLoadPreset = async (name, type) => {
        // 1. Optimistic UI update: immediately update the select value
        setSelectedPresets(prev => ({ ...prev, [type]: name }));
        
        if (!name) return;

        const preset = presets.find(p => p.name === name && p.type === type);
        if (preset) {
            try {
                // 2. Get current config
                const currentConfig = await ApiService.getApiConfig();
                // 3. Merge preset config
                const newConfig = { ...currentConfig, ...preset.config };
                // 4. Update config
                await ApiService.updateApiConfig(newConfig);
                
                // Optional: Notify user
                console.log(`Loaded preset ${name} for ${type}`);
            } catch (e) {
                console.error("Failed to load preset", e);
                alert("加载预设失败");
            }
        }
    };

    return (
        <header className="h-14 border-b border-dark-700 flex items-center justify-between px-4 bg-dark-800 flex-shrink-0">
            <div className="flex items-center gap-4">
                <h1 className="text-lg font-bold text-white flex items-center gap-2">
                    <span className="text-accent">MochiAni</span>
                    <span className="text-sm font-normal text-gray-400">| {current?.name || '未选择项目'}</span>
                </h1>
                <div className="flex gap-2">
                    <div className="flex items-center gap-1">
                        <select
                            className="px-2 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 outline-none"
                            value={currentProjectId || ''}
                            onChange={(e) => onChangeProject && onChangeProject(e.target.value)}
                            title="切换项目"
                        >
                            {projects.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                        <button
                            className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600"
                            onClick={onCreateProject}
                            title="新建项目"
                        >
                            新建项目
                        </button>
                        <button
                            className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600"
                            onClick={onDuplicateProject}
                            title="复制项目"
                        >
                            复制
                        </button>
                        <button
                            className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600"
                            onClick={onRenameProject}
                            title="重命名项目"
                        >
                            重命名
                        </button>
                        <button
                            className="px-3 py-1 text-xs bg-red-900 text-red-200 rounded hover:bg-red-800"
                            onClick={onDeleteProject}
                            title="删除项目"
                        >
                            删除
                        </button>
                        <button
                            className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600"
                            onClick={onExportProject}
                            title="导出JSON"
                        >
                            导出
                        </button>
                        <button
                            className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600"
                            onClick={onImportProject}
                            title="导入JSON"
                        >
                            导入
                        </button>
                    </div>
                    <select
                        className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 outline-none"
                        value={current?.style || 'anime'}
                        onChange={(e) => onChangeStyle && onChangeStyle(e.target.value)}
                        title="项目风格"
                    >
                        <option value="anime">日漫</option>
                        <option value="chinese_anime">国风动漫</option>
                        <option value="manga">漫画</option>
                        <option value="realistic">写实</option>
                        <option value="real">真人</option>
                    </select>
                </div>
            </div>
            <div className="flex items-center gap-3 text-gray-400">
                {currentProjectId && (
                    <>
                        <div className="flex items-center gap-2 mr-2 border-r border-dark-700 pr-4">
                            <select
                                className="px-2 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 outline-none max-w-[100px]"
                                onChange={(e) => handleLoadPreset(e.target.value, 'text')}
                                value={selectedPresets.text}
                                title="文本模型预设"
                            >
                                <option value="">Text Model</option>
                                {presets.filter(p => p.type === 'text').map(p => (
                                    <option key={p.name} value={p.name}>{p.name}</option>
                                ))}
                            </select>
                            <select
                                className="px-2 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 outline-none max-w-[100px]"
                                onChange={(e) => handleLoadPreset(e.target.value, 'image')}
                                value={selectedPresets.image}
                                title="生图模型预设"
                            >
                                <option value="">Image Model</option>
                                {presets.filter(p => p.type === 'image').map(p => (
                                    <option key={p.name} value={p.name}>{p.name}</option>
                                ))}
                            </select>
                            <select
                                className="px-2 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 outline-none max-w-[100px]"
                                onChange={(e) => handleLoadPreset(e.target.value, 'video')}
                                value={selectedPresets.video}
                                title="视频模型预设"
                            >
                                <option value="">Video Model</option>
                                {presets.filter(p => p.type === 'video').map(p => (
                                    <option key={p.name} value={p.name}>{p.name}</option>
                                ))}
                            </select>
                        </div>
                        <button 
                            className="hover:text-white flex items-center gap-1 text-sm"
                            onClick={onOpenAssets}
                            title="资产管理"
                        >
                            <ImageIcon size={16}/> 资产管理
                        </button>
                    </>
                )}
                <button 
                    className="hover:text-white flex items-center gap-1 text-sm"
                    onClick={onOpenApiConfig}
                    title="API 配置"
                >
                    <Settings size={16}/> 设置
                </button>
            </div>
        </header>
    );
};

export default Header;
