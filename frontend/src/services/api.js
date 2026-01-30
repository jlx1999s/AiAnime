const API_BASE_URL = "/api";
const USE_MOCK = false; // Set to false to use real backend

const MockData = {
    characters: [
        { id: 'c1', name: '陈远 (外门弟子)', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Chen' },
        { id: 'c2', name: '神秘师兄', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Brother' },
        { id: 'c3', name: '陈远 (剑主)', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ChenMaster' },
    ],
    shots: [
        {
            id: 1,
            prompt: "0.1-3秒: 低角度，快速推拉镜头。陆远受到重力冲击向后滑行，身体在铺满碎石的练武场上划出一道尘土飞扬的轨迹。",
            dialogue: "陆远：滚去黑暗剑冢里自生自灭吧！",
            characters: ['c1'],
            scene: null,
            image_url: "https://placehold.co/300x169/25262b/FFF?text=Shot+1",
        },
        {
            id: 2,
            prompt: "镜头仰拍刻家入口，巨石上“刻家”二字布满剑痕，散发着森森寒气。",
            dialogue: "(深吸一口气)",
            characters: ['c1'],
            scene: null,
            image_url: "https://placehold.co/300x169/25262b/FFF?text=Shot+2",
        },
         {
            id: 3,
            prompt: "陆远(外门弟子)目光一凝，手中铁剑发出嗡鸣。(动作虔诚而专注)，眼神中光影飞速流转，代表时间流逝。",
            dialogue: "“这就是...剑意？”",
            characters: ['c1', 'c2'],
            scene: null,
            image_url: "https://placehold.co/300x169/25262b/FFF?text=Shot+3",
        }
    ]
};

export const ApiService = {
    getProjects: async () => {
        if (USE_MOCK) {
            return [{
                id: "default_project",
                name: "守墓五年",
                style: "anime",
                shots: MockData.shots,
                characters: MockData.characters,
                scenes: []
            }];
        }
        const res = await fetch(`${API_BASE_URL}/projects`);
        return res.json();
    },

    createProject: async (name, style = "anime") => {
        if (USE_MOCK) {
            return {
                id: `proj_${Date.now()}`,
                name,
                style,
                shots: [],
                characters: [],
                scenes: []
            };
        }
        const res = await fetch(`${API_BASE_URL}/projects`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, style })
        });
        return res.json();
    },

    updateProject: async (projectId, updates) => {
        if (USE_MOCK) return { id: projectId, ...updates };
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updates)
        });
        return res.json();
    },

    deleteProject: async (projectId) => {
        if (USE_MOCK) return true;
        await fetch(`${API_BASE_URL}/projects/${projectId}`, { method: 'DELETE' });
        return true;
    },
    getProject: async (id) => {
        if (USE_MOCK) {
            return new Promise(resolve => setTimeout(() => resolve({
                id, 
                name: "守墓五年", 
                shots: MockData.shots, 
                characters: MockData.characters
            }), 500));
        }
        const res = await fetch(`${API_BASE_URL}/projects/${id}`);
        return res.json();
    },

    createShot: async (projectId, shotData) => {
        if (USE_MOCK) {
            return {
                id: Date.now(),
                ...shotData,
                preview: "https://placehold.co/300x169/25262b/FFF?text=New+Shot"
            };
        }
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}/shots`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(shotData)
        });
        return res.json();
    },

    updateShot: async (projectId, shotId, updates) => {
        if (USE_MOCK) return updates; // In mock we just return what we sent
        const res = await fetch(`${API_BASE_URL}/shots/${projectId}/${shotId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updates)
        });
        return res.json();
    },

    reorderShots: async (projectId, shotIds) => {
        if (USE_MOCK) return shotIds;
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}/shots/reorder`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ shot_ids: shotIds })
        });
        return res.json();
    },

    deleteShot: async (projectId, shotId) => {
        if (USE_MOCK) return true;
        await fetch(`${API_BASE_URL}/shots/${projectId}/${shotId}`, { method: 'DELETE' });
        return true;
    },

    generate: async (projectId, shotId, type, count) => {
        if (USE_MOCK) {
            return new Promise(resolve => setTimeout(() => resolve({ status: 'queued', video_id: type === 'video' ? `video_${Date.now()}` : null }), 1000));
        }
        const res = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ project_id: projectId, shot_id: shotId, type, count })
        });
        return res.json();
    },

    selectShotImage: async (projectId, shotId, imageUrl) => {
        if (USE_MOCK) {
            return { id: shotId, image_url: imageUrl };
        }
        const res = await fetch(`${API_BASE_URL}/shots/${projectId}/${shotId}/select-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_url: imageUrl })
        });
        return res.json();
    },

    removeShotImage: async (projectId, shotId, imageUrl, removeAll = false) => {
        if (USE_MOCK) {
            return { id: shotId, image_url: null, image_candidates: [] };
        }
        const res = await fetch(`${API_BASE_URL}/shots/${projectId}/${shotId}/remove-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_url: imageUrl, remove_all: removeAll })
        });
        return res.json();
    },

    removeShotVideo: async (projectId, shotId, videoId, url, removeAll = false) => {
        if (USE_MOCK) {
            return { id: shotId, video_url: null, video_items: [] };
        }
        const res = await fetch(`${API_BASE_URL}/shots/${projectId}/${shotId}/remove-video`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: videoId, url, remove_all: removeAll })
        });
        return res.json();
    },

    exportProjectVideo: async (projectId) => {
        if (USE_MOCK) {
            // Return mock zip URL
            return { url: `https://placehold.co/600x400/25262b/FFF?text=Mock+Export`, type: 'zip' };
        }
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}/export-video`, {
            method: 'POST'
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `导出失败 (${res.status})`);
        }
        return res.json();
    },

    generateAsset: async (prompt, type, projectId) => {
        if (USE_MOCK) return "https://placehold.co/512";
        const res = await fetch(`${API_BASE_URL}/api/generate-asset`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ prompt, type, project_id: projectId })
        });
        const data = await res.json();
        return data;
    },

    uploadFile: async (file, projectId) => {
        if (USE_MOCK) return "https://placehold.co/200";
        const formData = new FormData();
        formData.append('file', file);
        const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
        const res = await fetch(`${API_BASE_URL}/upload${q}`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        return data.url;
    },

    createCharacter: async (projectId, charData) => {
        if (USE_MOCK) return charData;
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}/characters`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(charData)
        });
        return res.json();
    },

    updateCharacter: async (projectId, charId, updates) => {
        if (USE_MOCK) return updates;
        const res = await fetch(`${API_BASE_URL}/characters/${projectId}/${charId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updates)
        });
        return res.json();
    },
    
    deleteCharacter: async (projectId, charId) => {
        if (USE_MOCK) return true;
        const res = await fetch(`${API_BASE_URL}/characters/${projectId}/${charId}`, {
            method: 'DELETE'
        });
        return res.json();
    },

    createScene: async (projectId, sceneData) => {
        if (USE_MOCK) return sceneData;
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}/scenes`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(sceneData)
        });
        return res.json();
    },

    updateScene: async (projectId, sceneId, updates) => {
        if (USE_MOCK) return updates;
        const res = await fetch(`${API_BASE_URL}/scenes/${projectId}/${sceneId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updates)
        });
        return res.json();
    },

    parseScript: async (content) => {
        if (USE_MOCK) {
            return new Promise(resolve => setTimeout(() => {
                const lines = content.split('\n').filter(l => l.trim());
                resolve(lines.map(l => ({
                    prompt: l,
                    dialogue: "",
                    characters: [],
                    scene: null
                })));
            }, 1000));
        }
        const res = await fetch(`${API_BASE_URL}/api/parse-script`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content })
        });
        return res.json();
    },

    getApiConfig: async () => {
        if (USE_MOCK) {
            return {
                text_provider: 'openai',
                openai_api_key: 'sk-mock',
                openai_model: 'gpt-3.5-turbo'
            };
        }
        const res = await fetch(`${API_BASE_URL}/api/config`);
        return res.json();
    },

    updateApiConfig: async (config) => {
        if (USE_MOCK) return config;
        const res = await fetch(`${API_BASE_URL}/api/config`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        return res.json();
    },

    getApiPresets: async () => {
        if (USE_MOCK) return [];
        const res = await fetch(`${API_BASE_URL}/api/presets`);
        return res.json();
    },

    saveApiPreset: async (name, type, config) => {
        if (USE_MOCK) return { name, type, config };
        const res = await fetch(`${API_BASE_URL}/api/presets`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, type, config })
        });
        return res.json();
    },

    deleteApiPreset: async (name, type) => {
        if (USE_MOCK) return true;
        await fetch(`${API_BASE_URL}/api/presets/${type}/${name}`, { method: 'DELETE' });
        return true;
    },

    uploadFile: async (file, projectId) => {
        if (USE_MOCK) return { url: URL.createObjectURL(file) };
        const formData = new FormData();
        formData.append('file', file);
        if (projectId) {
            formData.append('project_id', projectId);
        }
        const res = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        return res.json();
    },
};
