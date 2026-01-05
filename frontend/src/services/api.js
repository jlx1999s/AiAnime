const API_BASE_URL = "http://localhost:8001";
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

    deleteShot: async (projectId, shotId) => {
        if (USE_MOCK) return true;
        await fetch(`${API_BASE_URL}/shots/${projectId}/${shotId}`, { method: 'DELETE' });
        return true;
    },

    generate: async (shotId, type) => {
        if (USE_MOCK) {
            return new Promise(resolve => setTimeout(() => resolve({ status: 'queued' }), 1000));
        }
        const res = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ shot_id: shotId, type })
        });
        return res.json();
    },

    uploadFile: async (file) => {
        if (USE_MOCK) return "https://placehold.co/200";
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_BASE_URL}/upload`, {
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
    }
};
