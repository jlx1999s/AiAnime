import React, { useState, useEffect } from 'react';
import { ApiService } from '../services/api';
import { Settings, X, Save, Trash2 } from 'lucide-react';

const ApiConfigModal = ({ isOpen, onClose }) => {
    const [config, setConfig] = useState({
        dashscope_api_key: '',
        volc_access_key: '',
        volc_secret_key: '',
        text_provider: 'openai',
        image_provider: 'openai',
        video_provider: 'openai',
        openai_api_base: '',
        openai_api_key: '',
        openai_model: '',
        openai_image_api_base: '',
        openai_image_api_key: '',
        openai_image_model: '',
        openai_video_api_base: '',
        openai_video_api_key: '',
        openai_video_model: '',
        openai_video_endpoint: '',
        volc_image_model: 'jimeng_t2i_v30',
        volc_video_model: 'jimeng_i2v_first_v30',
        vectorengine_api_key: '',
        vectorengine_image_model: 'flux-1/dev',
        vectorengine_api_base: 'https://api.vectorengine.ai',
        rongyiyun_token: '',
        rongyiyun_api_base: 'https://zcbservice.aizfw.cn/kyyApi',
        rongyiyun_ratio: '16:9',
        rongyiyun_duration: 10
    });
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [applying, setApplying] = useState(false);
    const [applySuccess, setApplySuccess] = useState(false);
    const [activeTab, setActiveTab] = useState('text'); // text, image, video
    const [presets, setPresets] = useState([]);
    const [currentPreset, setCurrentPreset] = useState({ text: '', image: '', video: '' });
    
    // Define relevant fields for each tab type
    const CONFIG_FIELDS = {
        text: ['text_provider', 'openai_api_base', 'openai_api_key', 'openai_model', 'dashscope_api_key'],
        image: ['image_provider', 'openai_image_api_base', 'openai_image_api_key', 'openai_image_model', 'volc_access_key', 'volc_secret_key', 'volc_image_model', 'vectorengine_api_key', 'vectorengine_image_model', 'vectorengine_api_base'],
        video: ['video_provider', 'openai_video_api_base', 'openai_video_api_key', 'openai_video_model', 'openai_video_endpoint', 'volc_access_key', 'volc_secret_key', 'volc_video_model', 'rongyiyun_token', 'rongyiyun_api_base', 'rongyiyun_ratio', 'rongyiyun_duration']
    };

    useEffect(() => {
        if (isOpen) {
            loadConfig();
            loadPresets();
        }
    }, [isOpen]);

    const loadConfig = async () => {
        setLoading(true);
        try {
            const data = await ApiService.getApiConfig();
            if (data) {
                setConfig(prev => ({...prev, ...data}));
            }
        } catch (e) {
            console.error("Failed to load config", e);
        } finally {
            setLoading(false);
        }
    };

    const loadPresets = async () => {
        try {
            const data = await ApiService.getApiPresets();
            setPresets(data || []);
        } catch (e) {
            console.error("Failed to load presets", e);
        }
    };

    const handleLoadPreset = (name, type) => {
        if (!name) return;
        const preset = presets.find(p => p.name === name && p.type === type);
        if (preset) {
            setConfig(prev => ({...prev, ...preset.config}));
            setCurrentPreset(prev => ({...prev, [type]: name}));
        }
    };

    const handleSaveAsPreset = async (type) => {
        const defaultName = currentPreset[type] || '';
        const name = prompt("请输入预设名称：", defaultName);
        if (!name) return;
        
        // Extract only relevant fields for this type
        const fields = CONFIG_FIELDS[type] || [];
        const presetConfig = {};
        fields.forEach(field => {
            if (config[field] !== undefined) {
                presetConfig[field] = config[field];
            }
        });

        try {
            await ApiService.saveApiPreset(name, type, presetConfig);
            await loadPresets();
            setCurrentPreset(prev => ({...prev, [type]: name}));
            alert("预设保存成功");
        } catch (e) {
            console.error(e);
            alert("预设保存失败");
        }
    };

    const handleDeletePreset = async (type) => {
        const name = currentPreset[type];
        if (!name) return;
        if (!confirm(`确定删除预设 "${name}" 吗？`)) return;
        try {
            await ApiService.deleteApiPreset(name, type);
            await loadPresets();
            setCurrentPreset(prev => ({...prev, [type]: ''}));
        } catch (e) {
            console.error(e);
            alert("删除失败");
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await ApiService.updateApiConfig(config);
            onClose();
        } catch (e) {
            console.error("Failed to save config", e);
            alert("保存失败");
        } finally {
            setSaving(false);
        }
    };

    const handleApply = async () => {
        setApplying(true);
        try {
            await ApiService.updateApiConfig(config);
            setApplySuccess(true);
            setTimeout(() => setApplySuccess(false), 2000);
        } catch (e) {
            console.error("Failed to apply config", e);
            alert("应用失败");
        } finally {
            setApplying(false);
        }
    };

    if (!isOpen) return null;
    if (!config) return null;

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-dark-800 border border-dark-700 rounded-lg w-[500px] flex flex-col shadow-2xl">
                <div className="flex justify-between items-center p-4 border-b border-dark-700">
                    <h2 className="text-gray-200 font-medium flex items-center gap-2">
                        API 配置
                    </h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-white px-2">
                        ✕
                    </button>
                </div>

                {/* Presets Bar Removed */}
                
                {/* Tabs */}
                <div className="flex border-b border-dark-700 px-4 gap-4 pt-4">
                    <button 
                        onClick={() => setActiveTab('text')}
                        className={`py-3 text-sm border-b-2 transition-colors ${activeTab === 'text' ? 'border-accent text-accent' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
                    >
                        文本模型
                    </button>
                    <button 
                        onClick={() => setActiveTab('image')}
                        className={`py-3 text-sm border-b-2 transition-colors ${activeTab === 'image' ? 'border-accent text-accent' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
                    >
                        生图模型
                    </button>
                    <button 
                        onClick={() => setActiveTab('video')}
                        className={`py-3 text-sm border-b-2 transition-colors ${activeTab === 'video' ? 'border-accent text-accent' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
                    >
                        视频模型
                    </button>
                </div>

                <div className="p-6 space-y-6 h-[400px] overflow-y-auto">
                    {loading ? (
                        <div className="flex justify-center py-8 text-gray-500">
                            Loading...
                        </div>
                    ) : (
                        <>
                            {activeTab === 'text' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-200">
                                    <div className="flex items-center justify-between border-b border-dark-700 pb-2">
                                        <h3 className="text-xs font-bold text-accent uppercase">文本解析模型 (LLM)</h3>
                                        
                                        <div className="flex items-center gap-2">
                                            <select 
                                                className="bg-dark-900 text-gray-400 text-xs py-1 px-2 rounded border border-dark-600 focus:border-accent focus:outline-none"
                                                onChange={(e) => handleLoadPreset(e.target.value, 'text')}
                                                value={currentPreset.text}
                                            >
                                                <option value="">加载预设...</option>
                                                {presets.filter(p => p.type === 'text').map(p => (
                                                    <option key={p.name} value={p.name}>{p.name}</option>
                                                ))}
                                            </select>
                                            
                                            <button 
                                                onClick={() => handleSaveAsPreset('text')}
                                                className="p-1 hover:text-white text-gray-400"
                                                title="保存当前配置为预设"
                                            >
                                                <Save size={14} />
                                            </button>

                                            {currentPreset.text && (
                                                <button 
                                                    onClick={() => handleDeletePreset('text')}
                                                    className="p-1 hover:text-red-400 text-gray-400"
                                                    title={`删除预设 ${currentPreset.text}`}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">提供方</label>
                                        <select
                                            value={config.text_provider || 'openai'}
                                            onChange={(e) => setConfig({...config, text_provider: e.target.value})}
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                        >
                                            <option value="openai">OpenAI</option>
                                            <option value="dashscope">DashScope</option>
                                        </select>
                                    </div>

                                    {/* OpenAI Config */}
                                    <div className="space-y-3">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">OpenAI Base URL</label>
                                                <input 
                                                    type="text"
                                                    value={config.openai_api_base || ''}
                                                    onChange={(e) => setConfig({...config, openai_api_base: e.target.value})}
                                                    placeholder="https://api.openai.com/v1"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                             <div>
                                                <label className="block text-xs text-gray-500 mb-1">Model Name</label>
                                                <input 
                                                    type="text"
                                                    value={config.openai_model || ''}
                                                    onChange={(e) => setConfig({...config, openai_model: e.target.value})}
                                                    placeholder="gpt-4o"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">OpenAI API Key</label>
                                            <input 
                                                type="password"
                                                value={config.openai_api_key || ''}
                                                onChange={(e) => setConfig({...config, openai_api_key: e.target.value})}
                                                placeholder="sk-..."
                                                className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                            />
                                        </div>
                                    </div>

                                    <div className="relative flex items-center">
                                        <div className="flex-grow border-t border-dark-700"></div>
                                        <span className="flex-shrink-0 mx-2 text-dark-500 text-[10px]">OR USE DASHSCOPE</span>
                                        <div className="flex-grow border-t border-dark-700"></div>
                                    </div>

                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">DashScope API Key</label>
                                        <input 
                                            type="password"
                                            value={config.dashscope_api_key || ''}
                                            onChange={(e) => setConfig({...config, dashscope_api_key: e.target.value})}
                                            placeholder="sk-..."
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                        />
                                    </div>
                                </div>
                            )}

                            {activeTab === 'image' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-200">
                                    <div className="flex items-center justify-between border-b border-dark-700 pb-2">
                                        <h3 className="text-xs font-bold text-accent uppercase">生图模型 (OpenAI Compatible)</h3>
                                        
                                        <div className="flex items-center gap-2">
                                            <select 
                                                className="bg-dark-900 text-gray-400 text-xs py-1 px-2 rounded border border-dark-600 focus:border-accent focus:outline-none"
                                                onChange={(e) => handleLoadPreset(e.target.value, 'image')}
                                                value={currentPreset.image}
                                            >
                                                <option value="">加载预设...</option>
                                                {presets.filter(p => p.type === 'image').map(p => (
                                                    <option key={p.name} value={p.name}>{p.name}</option>
                                                ))}
                                            </select>
                                            
                                            <button 
                                                onClick={() => handleSaveAsPreset('image')}
                                                className="p-1 hover:text-white text-gray-400"
                                                title="保存当前配置为预设"
                                            >
                                                <Save size={14} />
                                            </button>

                                            {currentPreset.image && (
                                                <button 
                                                    onClick={() => handleDeletePreset('image')}
                                                    className="p-1 hover:text-red-400 text-gray-400"
                                                    title={`删除预设 ${currentPreset.image}`}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">提供方</label>
                                        <select
                                            value={config.image_provider || 'openai'}
                                            onChange={(e) => setConfig({...config, image_provider: e.target.value})}
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                        >
                                            <option value="openai">OpenAI</option>
                                            <option value="vectorengine">VectorEngine (Fal-ai)</option>
                                            <option value="volcengine">Volcengine</option>
                                        </select>
                                    </div>

                                    {config.image_provider === 'vectorengine' && (
                                        <div className="space-y-3 p-3 bg-dark-800 rounded border border-dark-700 animate-in fade-in slide-in-from-top-2">
                                            <h4 className="text-xs font-bold text-accent uppercase mb-2">VectorEngine Config</h4>
                                            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded text-xs text-blue-200 mb-2">
                                                使用 Fal-ai 兼容接口 (VectorEngine) 生成图片。
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Base URL (中转域名)</label>
                                                <input 
                                                    type="text"
                                                    value={config.vectorengine_api_base || 'https://api.vectorengine.ai'}
                                                    onChange={(e) => setConfig({...config, vectorengine_api_base: e.target.value})}
                                                    placeholder="https://api.vectorengine.ai"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">API Key (Bearer Token)</label>
                                                <input 
                                                    type="password"
                                                    value={config.vectorengine_api_key || ''}
                                                    onChange={(e) => setConfig({...config, vectorengine_api_key: e.target.value})}
                                                    placeholder="your-key"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Model (e.g. flux-1/dev)</label>
                                                <input 
                                                    type="text"
                                                    value={config.vectorengine_image_model || 'flux-1/dev'}
                                                    onChange={(e) => setConfig({...config, vectorengine_image_model: e.target.value})}
                                                    placeholder="flux-1/dev"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    <div className="space-y-3">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">OpenAI Base URL</label>
                                                <input 
                                                    type="text"
                                                    value={config.openai_image_api_base || ''}
                                                    onChange={(e) => setConfig({...config, openai_image_api_base: e.target.value})}
                                                    placeholder="https://api.openai.com/v1"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Model Name</label>
                                                <input 
                                                    type="text"
                                                    value={config.openai_image_model || ''}
                                                    onChange={(e) => setConfig({...config, openai_image_model: e.target.value})}
                                                    placeholder="gpt-image-1"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">OpenAI API Key</label>
                                            <input 
                                                type="password"
                                                value={config.openai_image_api_key || ''}
                                                onChange={(e) => setConfig({...config, openai_image_api_key: e.target.value})}
                                                placeholder="sk-..."
                                                className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                            />
                                        </div>
                                    </div>

                                    <div className="relative flex items-center">
                                        <div className="flex-grow border-t border-dark-700"></div>
                                        <span className="flex-shrink-0 mx-2 text-dark-500 text-[10px]">OR USE VOLCENGINE</span>
                                        <div className="flex-grow border-t border-dark-700"></div>
                                    </div>

                                    <h3 className="text-xs font-bold text-accent uppercase border-b border-dark-700 pb-2">生图模型 (Volcengine)</h3>
                                    
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">Model Version</label>
                                        <select
                                            value={config.volc_image_model || 'jimeng_t2i_v30'}
                                            onChange={(e) => setConfig({...config, volc_image_model: e.target.value})}
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                        >
                                            <option value="jimeng_t2i_v30">Jimeng T2I v3.0 (Standard)</option>
                                            <option value="jimeng_t2i_v40">Jimeng T2I v4.0 (Enhanced)</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">Access Key (AK)</label>
                                        <input 
                                            type="password"
                                            value={config.volc_access_key || ''}
                                            onChange={(e) => setConfig({...config, volc_access_key: e.target.value})}
                                            placeholder="AK..."
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-3 rounded border border-dark-700 outline-none focus:border-accent"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">Secret Key (SK)</label>
                                        <input 
                                            type="password"
                                            value={config.volc_secret_key || ''}
                                            onChange={(e) => setConfig({...config, volc_secret_key: e.target.value})}
                                            placeholder="SK..."
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-3 rounded border border-dark-700 outline-none focus:border-accent"
                                        />
                                    </div>
                                    <p className="text-[10px] text-gray-500 italic">* AccessKey and SecretKey are shared with Video Model</p>
                                </div>
                            )}

                            {activeTab === 'video' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-200">
                                    <div className="flex items-center justify-between border-b border-dark-700 pb-2">
                                        <h3 className="text-xs font-bold text-accent uppercase">视频模型 (OpenAI Compatible)</h3>
                                        <div className="flex items-center gap-2">
                                            <select 
                                                className="bg-dark-900 text-gray-400 text-xs py-1 px-2 rounded border border-dark-600 focus:border-accent focus:outline-none"
                                                onChange={(e) => handleLoadPreset(e.target.value, 'video')}
                                                value={currentPreset.video}
                                            >
                                                <option value="">加载预设...</option>
                                                {presets.filter(p => p.type === 'video').map(p => (
                                                    <option key={p.name} value={p.name}>{p.name}</option>
                                                ))}
                                            </select>
                                            <button 
                                                onClick={() => handleSaveAsPreset('video')}
                                                className="p-1 hover:text-white text-gray-400"
                                                title="保存当前配置为预设"
                                            >
                                                <Save size={14} />
                                            </button>
                                            {currentPreset.video && (
                                                <button 
                                                    onClick={() => handleDeletePreset('video')}
                                                    className="p-1 hover:text-red-400 text-gray-400"
                                                    title={`删除预设 ${currentPreset.video}`}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">提供方</label>
                                        <select
                                            value={config.video_provider || 'openai'}
                                            onChange={(e) => setConfig({...config, video_provider: e.target.value})}
                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                        >
                                            <option value="openai">OpenAI</option>
                                            <option value="volcengine">Volcengine</option>
                                            <option value="rongyiyun">RongYiYun</option>
                                        </select>
                                    </div>

                                    {config.video_provider === 'openai' && (
                                        <>
                                            <h3 className="text-xs font-bold text-accent uppercase border-b border-dark-700 pb-2">视频模型 (OpenAI Compatible)</h3>
                                            <div className="space-y-3">
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label className="block text-xs text-gray-500 mb-1">OpenAI Base URL</label>
                                                        <input 
                                                            type="text"
                                                            value={config.openai_video_api_base || ''}
                                                            onChange={(e) => setConfig({...config, openai_video_api_base: e.target.value})}
                                                            placeholder="https://api.openai.com/v1"
                                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-xs text-gray-500 mb-1">Model Name</label>
                                                        <input 
                                                            type="text"
                                                            value={config.openai_video_model || ''}
                                                            onChange={(e) => setConfig({...config, openai_video_model: e.target.value})}
                                                            placeholder="gpt-video-1"
                                                            className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                        />
                                                    </div>
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-500 mb-1">Endpoint</label>
                                                    <input 
                                                        type="text"
                                                        value={config.openai_video_endpoint || ''}
                                                        onChange={(e) => setConfig({...config, openai_video_endpoint: e.target.value})}
                                                        placeholder="/videos/generations"
                                                        className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-500 mb-1">OpenAI API Key</label>
                                                    <input 
                                                        type="password"
                                                        value={config.openai_video_api_key || ''}
                                                        onChange={(e) => setConfig({...config, openai_video_api_key: e.target.value})}
                                                        placeholder="sk-..."
                                                        className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                    />
                                                </div>
                                            </div>
                                        </>
                                    )}

                                    {config.video_provider === 'volcengine' && (
                                        <>
                                            <h3 className="text-xs font-bold text-accent uppercase border-b border-dark-700 pb-2">视频模型 (Volcengine)</h3>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Model Version</label>
                                                <select
                                                    value={config.volc_video_model || 'jimeng_i2v_first_v30'}
                                                    onChange={(e) => setConfig({...config, volc_video_model: e.target.value})}
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                >
                                                    <option value="jimeng_i2v_first_v30">Jimeng I2V First v3.0</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Access Key (AK)</label>
                                                <input 
                                                    type="password"
                                                    value={config.volc_access_key || ''}
                                                    onChange={(e) => setConfig({...config, volc_access_key: e.target.value})}
                                                    placeholder="AK..."
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-3 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Secret Key (SK)</label>
                                                <input 
                                                    type="password"
                                                    value={config.volc_secret_key || ''}
                                                    onChange={(e) => setConfig({...config, volc_secret_key: e.target.value})}
                                                    placeholder="SK..."
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-3 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <p className="text-[10px] text-gray-500 italic">* AccessKey and SecretKey are shared with Image Model</p>
                                        </>
                                    )}

                                    {config.video_provider === 'rongyiyun' && (
                                        <>
                                            <h3 className="text-xs font-bold text-accent uppercase border-b border-dark-700 pb-2">视频模型 (RongYiYun)</h3>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">API Base URL</label>
                                                <input
                                                    type="text"
                                                    value={config.rongyiyun_api_base || ''}
                                                    onChange={(e) => setConfig({...config, rongyiyun_api_base: e.target.value})}
                                                    placeholder="https://zcbservice.aizfw.cn/kyyApi"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs text-gray-500 mb-1">Token</label>
                                                <input
                                                    type="password"
                                                    value={config.rongyiyun_token || ''}
                                                    onChange={(e) => setConfig({...config, rongyiyun_token: e.target.value})}
                                                    placeholder="token"
                                                    className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                />
                                            </div>
                                            <div className="grid grid-cols-2 gap-3">
                                                <div>
                                                    <label className="block text-xs text-gray-500 mb-1">Ratio</label>
                                                    <select
                                                        value={config.rongyiyun_ratio || '16:9'}
                                                        onChange={(e) => setConfig({...config, rongyiyun_ratio: e.target.value})}
                                                        className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                    >
                                                        <option value="9:16">9:16</option>
                                                        <option value="16:9">16:9</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-500 mb-1">Duration</label>
                                                    <select
                                                        value={Number(config.rongyiyun_duration) || 10}
                                                        onChange={(e) => setConfig({...config, rongyiyun_duration: Number(e.target.value)})}
                                                        className="w-full bg-dark-900 text-gray-200 text-sm p-2 rounded border border-dark-700 outline-none focus:border-accent"
                                                    >
                                                        <option value={10}>10</option>
                                                        <option value={15}>15</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>

                <div className="p-4 border-t border-dark-700 flex justify-end gap-2">
                    <button 
                        onClick={onClose}
                        className="px-4 py-2 rounded text-sm text-gray-400 hover:text-white hover:bg-dark-700 transition-colors"
                    >
                        取消
                    </button>
                    <button 
                        onClick={handleApply}
                        disabled={loading || saving || applying}
                        className={`px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2 ${applySuccess ? 'bg-green-600/20 text-green-400 border border-green-600/50' : 'bg-dark-700 text-gray-200 hover:bg-dark-600'}`}
                    >
                        {applying && <span className="animate-spin">⟳</span>}
                        {applySuccess ? '已应用' : (applying ? '应用中...' : '应用')}
                    </button>
                    <button 
                        onClick={handleSave}
                        disabled={loading || saving}
                        className="px-6 py-2 rounded text-sm bg-accent text-white font-medium hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {saving && <span className="animate-spin">⟳</span>}
                        {saving ? '保存中...' : '保存配置'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ApiConfigModal;
