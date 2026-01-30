import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Film, ChevronLeft } from 'lucide-react';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ShotListHeader from '../components/ShotListHeader';
import ShotItem from '../components/ShotItem';
import AddScriptModal from '../components/AddScriptModal';
import GenerateAssetModal from '../components/GenerateAssetModal';
import ApiConfigModal from '../components/ApiConfigModal';
import { ApiService } from '../services/api';

const normalizeShot = (shot) => {
    const items = Array.isArray(shot.video_items) ? shot.video_items : [];
    if (items.length === 0 && shot.video_url) {
        return {
            ...shot,
            video_items: [
                {
                    id: 'legacy',
                    url: shot.video_url,
                    progress: shot.video_progress ?? null,
                    status: shot.status
                }
            ]
        };
    }
    return shot;
};

const ProjectEditor = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    
    const [shots, setShots] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isScriptModalOpen, setIsScriptModalOpen] = useState(false);
    const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
    const [isApiConfigOpen, setIsApiConfigOpen] = useState(false);
    const [generateType, setGenerateType] = useState('character'); // 'character' or 'scene'
    const [regenerateAssetData, setRegenerateAssetData] = useState(null);
    const [selectedCharId, setSelectedCharId] = useState(null);
    const [selectedSceneId, setSelectedSceneId] = useState(null);
    const [selectedShotId, setSelectedShotId] = useState(null);
    const [projects, setProjects] = useState([]);
    const [isGeneratingCharacters, setIsGeneratingCharacters] = useState(false);
    const [isGeneratingScenes, setIsGeneratingScenes] = useState(false);
    const [isGeneratingStoryboards, setIsGeneratingStoryboards] = useState(false);
    const [selectedShots, setSelectedShots] = useState(new Set());
    
    // Project Settings
    const [defaultSceneId, setDefaultSceneId] = useState(null);
    const [defaultPanelLayout, setDefaultPanelLayout] = useState('1-panel');
    const [defaultImageCount, setDefaultImageCount] = useState(3);
    
    // File Inputs
    const fileInputRef = React.useRef(null);
    const sceneFileInputRef = React.useRef(null);
    const shotFileInputRef = React.useRef(null);
    const newCharFileInputRef = React.useRef(null);
    const newSceneFileInputRef = React.useRef(null);
    const importFileInputRef = React.useRef(null);

    const loadProjects = async () => {
        try {
            const list = await ApiService.getProjects();
            setProjects(list);
        } catch (e) {
            console.error("Failed to load projects", e);
        }
    };

    // Load initial data
    useEffect(() => {
        loadProjects();
    }, []);

    useEffect(() => {
        const loadData = async () => {
            if (!projectId) return;
            setLoading(true);
            try {
                const project = await ApiService.getProject(projectId);
                if (!project || !project.id) {
                    alert("项目不存在");
                    navigate('/');
                    return;
                }
                setShots((project.shots || []).map(normalizeShot));
                setCharacters(project.characters || []);
                setScenes(project.scenes || []);
                setDefaultSceneId(project.default_scene_id || null);
                setDefaultPanelLayout(project.default_panel_layout || '1-panel');
                setDefaultImageCount(project.default_image_count || 3);
                setSelectedShots(new Set());
            } catch (error) {
                console.error("Failed to load project", error);
                // navigate('/');
            }
            setLoading(false);
        };
        loadData();
    }, [projectId, navigate]);

    const handleSelectShot = (id, selected) => {
        setSelectedShots(prev => {
            const newSet = new Set(prev);
            if (selected) newSet.add(id);
            else newSet.delete(id);
            return newSet;
        });
    };

    const handleSelectAllShots = (selected) => {
        if (selected) {
            setSelectedShots(new Set(shots.map(s => s.id)));
        } else {
            setSelectedShots(new Set());
        }
    };

    const handleGenerateAllCharacters = async () => {
        const targets = characters.filter(c => !c.avatar_url || c.avatar_url.includes('dicebear'));
        const targetList = targets.length > 0 ? targets : characters;
        
        if (!confirm(`确定要为 ${targetList.length} 个角色生成图片吗？`)) return;

        setIsGeneratingCharacters(true);
        const currentProject = projects.find(p => p.id === projectId);
        const style = currentProject?.style || 'anime';
        
        try {
            for (const char of targetList) {
                const prompt = `${char.name}, ${char.prompt || char.description || 'character portrait'}, ${style} style, high quality`;
                try {
                    const result = await ApiService.generateAsset(prompt, 'character', projectId);
                    const updated = { avatar_url: result.url };
                    await ApiService.updateCharacter(projectId, char.id, { ...char, ...updated });
                    setCharacters(prev => prev.map(c => c.id === char.id ? { ...c, ...updated } : c));
                } catch (e) {
                    console.error(`Generate failed for ${char.name}`, e);
                }
            }
        } finally {
            setIsGeneratingCharacters(false);
        }
    };

    const handleGenerateAllScenes = async () => {
        const targets = scenes.filter(s => !s.image_url);
        const targetList = targets.length > 0 ? targets : scenes;

        if (!confirm(`确定要为 ${targetList.length} 个场景生成图片吗？`)) return;

        setIsGeneratingScenes(true);
        const currentProject = projects.find(p => p.id === projectId);
        const style = currentProject?.style || 'anime';

        try {
            for (const scene of targetList) {
                const prompt = `${scene.name}, ${scene.prompt || scene.description || 'scenery'}, ${style} style, high quality`;
                try {
                    const result = await ApiService.generateAsset(prompt, 'scene', projectId);
                    const updated = { image_url: result.url };
                    await ApiService.updateScene(projectId, scene.id, { ...scene, ...updated });
                    setScenes(prev => prev.map(s => s.id === scene.id ? { ...s, ...updated } : s));
                } catch (e) {
                    console.error(`Generate failed for ${scene.name}`, e);
                }
            }
        } finally {
            setIsGeneratingScenes(false);
        }
    };

    const handleGenerateAllStoryboards = async () => {
        const targets = shots.filter(s => !s.image_url || s.image_url.includes('placehold'));
        const targetList = targets.length > 0 ? targets : shots;

        if (!confirm(`确定要为 ${targetList.length} 个分镜生成图片吗？`)) return;

        setIsGeneratingStoryboards(true);
        try {
            // Process in batches or parallel
            const promises = targetList.map(shot => handleGenerate(shot.id, 'image', defaultImageCount, true));
            await Promise.all(promises);
        } finally {
            setIsGeneratingStoryboards(false);
        }
    };

    const handleMoveUp = async (index) => {
        if (index <= 0) return;
        const newShots = [...shots];
        [newShots[index - 1], newShots[index]] = [newShots[index], newShots[index - 1]];
        setShots(newShots);
        try {
            await ApiService.reorderShots(projectId, newShots.map(s => s.id));
        } catch (e) {
            console.error("Reorder failed", e);
        }
    };

    const handleMoveDown = async (index) => {
        if (index >= shots.length - 1) return;
        const newShots = [...shots];
        [newShots[index], newShots[index + 1]] = [newShots[index + 1], newShots[index]];
        setShots(newShots);
        try {
            await ApiService.reorderShots(projectId, newShots.map(s => s.id));
        } catch (e) {
            console.error("Reorder failed", e);
        }
    };

    const handleDelete = async (id) => {
        if(confirm('确定要删除这个镜头吗？')) {
            // Optimistic update
            const originalShots = [...shots];
            setShots(shots.filter(s => s.id !== id));
            try {
                await ApiService.deleteShot(projectId, id);
            } catch (e) {
                alert('删除失败');
                setShots(originalShots);
            }
        }
    };

    const handleUpdate = async (id, newShot) => {
        // Optimistic update
        setShots(shots.map(s => s.id === id ? newShot : s));
        // Debounce could be added here
        await ApiService.updateShot(projectId, id, newShot);
    };

    const handleDeleteShotImage = async (shotId, imageUrl, removeAll = false) => {
        const originalShots = [...shots];
        setShots(prev => prev.map(s => {
            if (s.id !== shotId) return s;
            if (removeAll) {
                return { ...s, image_url: null, image_candidates: [] };
            }
            const nextCandidates = Array.isArray(s.image_candidates)
                ? s.image_candidates.filter(u => u !== imageUrl)
                : [];
            const nextImage = s.image_url === imageUrl ? (nextCandidates[0] || null) : s.image_url;
            return { ...s, image_url: nextImage, image_candidates: nextCandidates };
        }));
        try {
            const updated = await ApiService.removeShotImage(projectId, shotId, imageUrl, removeAll);
            setShots(prev => prev.map(s => s.id === shotId ? normalizeShot(updated) : s));
        } catch (e) {
            alert('删除分镜失败');
            setShots(originalShots);
        }
    };

    const handleDeleteShotVideo = async (shotId, videoId, url, removeAll = false) => {
        const originalShots = [...shots];
        setShots(prev => prev.map(s => {
            if (s.id !== shotId) return s;
            if (removeAll) {
                return { ...s, video_url: null, video_items: [], video_progress: null };
            }
            const nextItems = Array.isArray(s.video_items)
                ? s.video_items.filter(v => v.id !== videoId)
                : [];
            const nextVideoUrl = s.video_url === url ? (nextItems.find(v => v.url)?.url || null) : s.video_url;
            return { ...s, video_items: nextItems, video_url: nextVideoUrl };
        }));
        try {
            const updated = await ApiService.removeShotVideo(projectId, shotId, videoId, url, removeAll);
            setShots(prev => prev.map(s => s.id === shotId ? normalizeShot(updated) : s));
        } catch (e) {
            alert('删除视频失败');
            setShots(originalShots);
        }
    };

    // Project Settings Handlers
    const handleSetDefaultScene = async (sceneId) => {
        if (!projectId) return;
        try {
            const newId = sceneId === defaultSceneId ? null : sceneId; // Toggle
            await ApiService.updateProject(projectId, { default_scene_id: newId });
            setDefaultSceneId(newId);
        } catch (error) {
            console.error("Failed to update default scene", error);
        }
    };

    const handleSetDefaultPanelLayout = async (layout) => {
        if (!projectId) return;
        
        // Optimistic update for UI
        setDefaultPanelLayout(layout);
        const originalShots = [...shots];
        setShots(prev => prev.map(s => ({ ...s, panel_layout: layout })));

        try {
            await ApiService.updateProject(projectId, { default_panel_layout: layout });
            
            // Update all shots in background
            const updatePromises = shots.map(s => 
                ApiService.updateShot(projectId, s.id, { ...s, panel_layout: layout })
            );
            await Promise.all(updatePromises);
        } catch (error) {
            console.error("Failed to update default panel layout", error);
            // Optional: Revert on catastrophic failure, but partial updates are tricky
            // setShots(originalShots); 
        }
    };

    const handleSetDefaultImageCount = async (count) => {
        if (!projectId) return;
        try {
            const newCount = parseInt(count, 10) || 4;
            await ApiService.updateProject(projectId, { default_image_count: newCount });
            setDefaultImageCount(newCount);
        } catch (error) {
            console.error("Failed to update default image count", error);
        }
    };

    const handleAddShot = async () => {
        const tempId = Date.now();
        const newShotData = {
            prompt: "",
            dialogue: "",
            characters: [],
            scene_id: defaultSceneId || null,
            use_scene_ref: true,
            panel_layout: defaultPanelLayout || '3-panel',
        };
        
        // Optimistic UI
        const optimisitcShot = {
             id: tempId, 
             ...newShotData, 
             image_url: "https://placehold.co/300x169/25262b/FFF?text=Loading..." 
        };
        setShots(prev => [...prev, optimisitcShot]);

        try {
            const createdShot = await ApiService.createShot(projectId, newShotData);
            // Replace temp ID with real one
            setShots(prev => prev.map(s => s.id === tempId ? normalizeShot(createdShot) : s));
        } catch (e) {
            console.error("Create failed", e);
        }
    };

    const handleGenerate = async (shotId, type, count, silent = false) => {
        if (type === 'video') {
            const shot = shots.find(s => s.id === shotId);
            const hasShotImage = !!shot?.image_url;
            if (!hasShotImage) {
                if (!silent) alert('请先生成或上传分镜图');
                return;
            }
        }
        if (!silent) alert(`正在请求后端生成 ${type}...`);
        setShots(prev => prev.map(s => s.id === shotId ? { ...s, status: 'generating', video_progress: type === 'video' ? 0 : s.video_progress } : s));
        const result = await ApiService.generate(projectId, shotId, type, count);
        if (type === 'video' && result?.video_id) {
            setShots(prev => prev.map(s => {
                if (s.id !== shotId) return s;
                const items = Array.isArray(s.video_items) ? [...s.video_items] : [];
                if (!items.some(v => v.id === result.video_id)) {
                    items.unshift({ id: result.video_id, progress: 0, status: 'generating' });
                }
                return { ...s, video_items: items };
            }));
        }

         const startedAt = Date.now();
         const timeoutMs = type === 'video' ? 5 * 60 * 1000 : 2 * 60 * 1000;

         while (Date.now() - startedAt < timeoutMs) {
             try {
                    const project = await ApiService.getProject(projectId);
                    const nextShot = (project.shots || []).find(s => s.id === shotId);
                    if (nextShot) {
                        setShots(prev => prev.map(s => s.id === shotId ? normalizeShot(nextShot) : s));
                        if (nextShot.status === 'completed' || nextShot.status === 'failed') {
                            return;
                        }
                 }
             } catch (e) {
                 console.error('Polling generation status failed', e);
             }
             await new Promise(r => setTimeout(r, 1500));
         }
    };

    const handleParseScript = async (content) => {
        try {
            const response = await ApiService.parseScript(content);
            
            // Handle both new object format and old array format (fallback)
            let newShots = [];
            let parsedCharacters = [];
            let parsedScenes = [];

            if (Array.isArray(response)) {
                newShots = response;
            } else {
                newShots = response.shots || [];
                parsedCharacters = response.characters || [];
                parsedScenes = response.scenes || [];
            }
            
            // 1. Extract unique character names (from parsed characters and shots)
            const allNames = new Set();
            parsedCharacters.forEach(c => allNames.add(c.name));
            newShots.forEach(s => {
                if (s.characters) {
                    s.characters.forEach(name => allNames.add(name));
                }
            });

            // 2. Process characters
            const charMap = {}; // Normalized Name -> ID
            const currentChars = [...characters];
            
            // Map existing characters first
            currentChars.forEach(c => {
                if (c.name) charMap[c.name.trim().toLowerCase()] = c.id;
            });

            // Create new characters for unknown names
            const newCharsToCreate = [];
            for (const name of allNames) {
                const normalizedName = name.trim().toLowerCase();
                
                // Fuzzy match for characters
                if (!charMap[normalizedName]) {
                    const candidates = currentChars.filter(c => {
                        const cName = c.name.trim().toLowerCase();
                        // Script: "Chen Yuan (Disciple)" -> Asset: "Chen Yuan"
                        return cName && normalizedName.includes(cName);
                    });
                    if (candidates.length > 0) {
                        candidates.sort((a, b) => b.name.length - a.name.length);
                        charMap[normalizedName] = candidates[0].id;
                    }
                }

                if (!charMap[normalizedName]) {
                    // Find parsed details for this character to get the prompt
                    const parsedChar = parsedCharacters.find(c => c.name === name);

                    const newChar = {
                        id: `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name.trim(),
                        avatar_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${name}`,
                        tags: [],
                        prompt: parsedChar ? parsedChar.prompt : "" // Use parsed prompt
                    };
                    newCharsToCreate.push(newChar);
                    charMap[normalizedName] = newChar.id; // Assign temp ID
                }
            }

            // Save new characters to backend
            for (const char of newCharsToCreate) {
                 await ApiService.createCharacter(projectId, char);
                 currentChars.push(char);
            }
            setCharacters(currentChars);

            // 2.5 Process Scenes
            const allScenes = new Set();
            parsedScenes.forEach(s => allScenes.add(s.name));
            newShots.forEach(s => {
                if (s.scene) allScenes.add(s.scene);
            });

            const sceneMap = {}; // Normalized Name -> ID
            const currentScenes = [...scenes];
            currentScenes.forEach(s => {
                if (s.name) sceneMap[s.name.trim().toLowerCase()] = s.id;
            });

            const newScenesToCreate = [];
            for (const name of allScenes) {
                const normalizedName = name.trim().toLowerCase();
                
                // Fuzzy match: Check if any existing scene name is part of the script scene name
                // e.g. Script: "Dark Forest Entrance" -> Matches Asset: "Forest"
                if (!sceneMap[normalizedName]) {
                    const candidates = currentScenes.filter(s => {
                        const sName = s.name.trim().toLowerCase();
                        // Try both directions for robustness
                        return sName && (normalizedName.includes(sName) || sName.includes(normalizedName));
                    });
                    
                    if (candidates.length > 0) {
                        // Pick the longest match (most specific)
                        candidates.sort((a, b) => b.name.length - a.name.length);
                        sceneMap[normalizedName] = candidates[0].id;
                    }
                }

                if (!sceneMap[normalizedName]) {
                    // Find parsed details for this scene to get the prompt
                    const parsedScene = parsedScenes.find(s => s.name === name);

                    const newScene = {
                        id: `scene_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name.trim(),
                        image_url: "", // Placeholder
                        tags: [],
                        prompt: parsedScene ? parsedScene.prompt : "" // Use parsed prompt
                    };
                    newScenesToCreate.push(newScene);
                    sceneMap[normalizedName] = newScene.id;
                }
            }
            
            for (const scene of newScenesToCreate) {
                await ApiService.createScene(projectId, scene);
                currentScenes.push(scene);
            }
            setScenes(currentScenes);

            // 3. Create shots with character IDs and Scene IDs
            const createdShots = [];
            for (const shotData of newShots) {
                // Replace names with IDs
                const charIds = (shotData.characters || [])
                    .map(name => charMap[name.trim().toLowerCase()])
                    .filter(Boolean);
                const sceneId = shotData.scene ? sceneMap[shotData.scene.trim().toLowerCase()] : null;

                // Append asset prompts to shot prompt
                let assetPrompts = "";
                const relevantChars = currentChars.filter(c => charIds.includes(c.id));
                relevantChars.forEach(c => {
                    if (c.prompt) assetPrompts += ` [${c.name}: ${c.prompt}]`;
                });
                if (sceneId) {
                    const s = currentScenes.find(sc => sc.id === sceneId);
                    if (s && s.prompt) assetPrompts += ` [${s.name}: ${s.prompt}]`;
                }

                const shotToCreate = { 
                    ...shotData, 
                    prompt: shotData.prompt + assetPrompts,
                    characters: charIds,
                    scene_id: sceneId,
                    use_scene_ref: true,
                    panel_layout: defaultPanelLayout || '1-panel'
                };
                
                const created = await ApiService.createShot(projectId, shotToCreate);
                
                // Double check: If scene_id was provided but not saved (e.g. backend model mismatch), 
                // explicitly update it.
                if (sceneId && !created.scene_id) {
                    await ApiService.updateShot(projectId, created.id, { scene_id: sceneId });
                    created.scene_id = sceneId;
                }
                
                createdShots.push(created);
            }
            
            setShots(prev => [...prev, ...createdShots]);
        } catch (e) {
            console.error("Script parse failed", e);
            alert("剧本解析失败");
        }
    };

    const onCharacterClick = (charId) => {
        setSelectedCharId(charId);
        fileInputRef.current?.click();
    };

    const onSceneClick = (sceneId) => {
        setSelectedSceneId(sceneId);
        sceneFileInputRef.current?.click();
    };

    const onShotImageClick = (shotId) => {
        setSelectedShotId(shotId);
        shotFileInputRef.current?.click();
    };

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file || !selectedCharId) return;

        try {
            const url = await ApiService.uploadFile(file, projectId);
            const char = characters.find(c => c.id === selectedCharId);
            if (char) {
                const updated = { ...char, avatar_url: url };
                await ApiService.updateCharacter(projectId, selectedCharId, updated);
                setCharacters(prev => prev.map(c => c.id === selectedCharId ? updated : c));
            }
        } catch (e) {
            console.error("Upload failed", e);
            alert("上传失败");
        }
        e.target.value = null;
    };

    const handleSceneFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file || !selectedSceneId) return;

        try {
            const url = await ApiService.uploadFile(file, projectId);
            const scene = scenes.find(s => s.id === selectedSceneId);
            if (scene) {
                const updated = { ...scene, image_url: url };
                await ApiService.updateScene(projectId, selectedSceneId, updated);
                setScenes(prev => prev.map(s => s.id === selectedSceneId ? updated : s));
            }
        } catch (e) {
            console.error("Upload failed", e);
            alert("场景上传失败");
        }
        e.target.value = null;
    };

    const handleShotFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file || !selectedShotId) return;

        try {
            const url = await ApiService.uploadFile(file, projectId);
            const shot = shots.find(s => s.id === selectedShotId);
            if (shot) {
                const updated = { ...shot, image_url: url };
                await ApiService.updateShot(projectId, selectedShotId, updated);
                setShots(prev => prev.map(s => s.id === selectedShotId ? updated : s));
            }
        } catch (e) {
            console.error("Upload failed", e);
            alert("分镜图片上传失败");
        }
        e.target.value = null;
    };

    const handleSelectShotCandidate = async (shotId, imageUrl) => {
        const previousShots = shots;
        setShots(prev => prev.map(s => s.id === shotId ? { ...s, image_url: imageUrl } : s));
        try {
            const updated = await ApiService.selectShotImage(projectId, shotId, imageUrl);
            setShots(prev => prev.map(s => s.id === shotId ? normalizeShot(updated) : s));
        } catch (e) {
            console.error("Select candidate failed", e);
            setShots(previousShots);
        }
    };

    const handleAddCharacterClick = () => {
        newCharFileInputRef.current?.click();
    };

    const handleAddSceneClick = () => {
        newSceneFileInputRef.current?.click();
    };

    const handleNewCharacterFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const name = window.prompt("请输入角色名称", "新角色");
        if (!name) return;

        try {
            const url = await ApiService.uploadFile(file, projectId);
            const newChar = {
                id: `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                name: name,
                avatar_url: url,
                tags: []
            };
            await ApiService.createCharacter(projectId, newChar);
            setCharacters(prev => [...prev, newChar]);
        } catch (e) {
            console.error("Create character failed", e);
            alert("创建角色失败");
        }
        e.target.value = null;
    };

    const handleNewSceneFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const name = window.prompt("请输入场景名称", "新场景");
        if (!name) return;

        try {
            const url = await ApiService.uploadFile(file);
            const newScene = {
                id: `scene_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                name: name,
                image_url: url,
                tags: []
            };
            await ApiService.createScene(projectId, newScene);
            setScenes(prev => [...prev, newScene]);
        } catch (e) {
            console.error("Create scene failed", e);
            alert("创建场景失败");
        }
        e.target.value = null;
    };

    const handleOpenGenerateModal = (type, existingData = null) => {
        setGenerateType(type);
        setRegenerateAssetData(existingData);
        setIsGenerateModalOpen(true);
    };

    const handleGenerateAsset = async (name, prompt, type) => {
        try {
            // 1. Call Generation API
            const result = await ApiService.generateAsset(prompt, type, projectId);
            const url = result.url;
            
            if (regenerateAssetData) {
                // Update existing asset
                if (type === 'character') {
                     const updated = { avatar_url: url, prompt: prompt };
                     await ApiService.updateCharacter(projectId, regenerateAssetData.id, { ...regenerateAssetData, ...updated });
                     setCharacters(prev => prev.map(c => c.id === regenerateAssetData.id ? { ...c, ...updated } : c));
                } else if (type === 'scene') {
                     const updated = { image_url: url, prompt: prompt };
                     await ApiService.updateScene(projectId, regenerateAssetData.id, updated);
                     setScenes(prev => prev.map(s => s.id === regenerateAssetData.id ? { ...s, ...updated } : s));
                }
            } else {
                // 2. Create Asset
                if (type === 'character') {
                    const newChar = {
                        id: `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name,
                        avatar_url: url,
                        tags: [],
                        prompt: prompt
                    };
                    await ApiService.createCharacter(projectId, newChar);
                    setCharacters(prev => [...prev, newChar]);
                } else if (type === 'scene') {
                    const newScene = {
                        id: `scene_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name,
                        image_url: url,
                        tags: [],
                        prompt: prompt
                    };
                    await ApiService.createScene(projectId, newScene);
                    setScenes(prev => [...prev, newScene]);
                }
            }
        } catch (e) {
            console.error("Generate asset failed", e);
            throw e; // Re-throw to be handled by modal
        }
    };

    if (loading) {
        return <div className="h-screen flex items-center justify-center bg-dark-900 text-gray-500">加载项目中...</div>;
    }

    return (
        <div className="flex flex-col h-screen overflow-hidden font-sans">
            <div className="bg-dark-800 border-b border-dark-700 px-2 py-1 flex items-center">
                <button 
                    onClick={() => navigate('/')} 
                    className="flex items-center text-gray-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-dark-700 transition-colors"
                >
                    <ChevronLeft size={14} className="mr-1"/> 返回项目列表
                </button>
            </div>
            <Header 
                projects={projects} 
                currentProjectId={projectId} 
                onChangeProject={(id) => navigate(`/project/${id}`)}
                onCreateProject={async () => {
                    const name = prompt("请输入新项目名称");
                    if (!name) return;
                    const created = await ApiService.createProject(name);
                    setProjects(prev => [created, ...prev]);
                    navigate(`/project/${created.id}`);
                }}
                onRenameProject={async () => {
                    if (!projectId) return;
                    const name = prompt("请输入新的项目名称");
                    if (!name) return;
                    const updated = await ApiService.updateProject(projectId, { name });
                    setProjects(prev => prev.map(p => p.id === projectId ? { ...p, name: updated.name || name } : p));
                }}
                onDeleteProject={async () => {
                    if (!projectId) return;
                    if (!confirm("确定删除当前项目？该操作不可恢复")) return;
                    await ApiService.deleteProject(projectId);
                    navigate('/');
                }}
                onChangeStyle={async (style) => {
                    if (!projectId) return;
                    const updated = await ApiService.updateProject(projectId, { style });
                    setProjects(prev => prev.map(p => p.id === projectId ? { ...p, style: updated.style || style } : p));
                }}
                onDuplicateProject={async () => {
                    if (!projectId) return;
                    const source = await ApiService.getProject(projectId);
                    const copyName = `${source.name} - 副本`;
                    const created = await ApiService.createProject(copyName, source.style || 'anime');
                    setProjects(prev => [created, ...prev]);
                    navigate(`/project/${created.id}`);
                    
                    const idMap = { chars: {}, scenes: {} };
                    for (const c of source.characters || []) {
                        const newChar = { ...c, id: `char_${Date.now()}_${Math.random().toString(36).slice(2, 9)}` };
                        await ApiService.createCharacter(created.id, newChar);
                        idMap.chars[c.id] = newChar.id;
                    }
                    for (const s of source.scenes || []) {
                        const newScene = { ...s, id: `scene_${Date.now()}_${Math.random().toString(36).slice(2, 9)}` };
                        await ApiService.createScene(created.id, newScene);
                        idMap.scenes[s.id] = newScene.id;
                    }
                    for (const shot of source.shots || []) {
                        const newShot = {
                            prompt: shot.prompt || "",
                            dialogue: shot.dialogue || "",
                            characters: (shot.characters || []).map(cid => idMap.chars[cid]).filter(Boolean),
                            scene_id: shot.scene_id ? idMap.scenes[shot.scene_id] : null,
                            image_url: shot.image_url || "",
                            video_url: shot.video_url || ""
                        };
                        await ApiService.createShot(created.id, newShot);
                    }
                }}
                onExportProject={() => {
                    if (!projectId) return;
                    const data = {
                        id: projectId,
                        shots,
                        characters,
                        scenes,
                        meta: projects.find(p => p.id === projectId) || {}
                    };
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${data.meta.name || 'project'}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                }}
                onImportProject={() => {
                    importFileInputRef.current?.click();
                }}
                onOpenApiConfig={() => setIsApiConfigOpen(true)}
                onOpenAssets={() => navigate(`/project/${projectId}/assets`)}
            />
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col min-w-0 bg-dark-900">
                    {/* Toolbar */}
                    <div className="h-10 border-b border-dark-700 flex items-center px-4 gap-4 bg-dark-800 text-xs text-gray-400 flex-shrink-0">
                        <span className="font-medium text-gray-300">共 {shots.length} 个镜头</span>
                        <div className="h-4 w-px bg-dark-600"></div>
                        <button onClick={() => setIsScriptModalOpen(true)} className="hover:text-white flex items-center gap-1 transition-colors">
                            <Film size={12}/> 添加剧本
                        </button>
                        <button onClick={handleAddShot} className="hover:text-white flex items-center gap-1 transition-colors">
                            <Plus size={12}/> 添加空白镜头
                        </button>
                        <div className="h-4 w-px bg-dark-600"></div>
                        <button 
                            className="hover:text-white flex items-center gap-1 transition-colors ml-auto text-accent"
                            onClick={async () => {
                                try {
                                    if (!projectId) return;
                                    const res = await ApiService.exportProjectVideo(projectId);
                                    const url = res?.url;
                                    if (!url) {
                                        alert("导出失败：返回结果为空");
                                        return;
                                    }
                                    // Open in new tab; browser will handle download for mp4/zip
                                    window.open(url, "_blank");
                                } catch (e) {
                                    alert(e.message || "导出失败");
                                }
                            }}
                        >
                            <Film size={12}/> 导出视频
                        </button>
                    </div>

                    {/* Shot List Header & Content */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <ShotListHeader 
                        allSelected={shots.length > 0 && selectedShots.size === shots.length}
                        onSelectAll={handleSelectAllShots}
                        defaultPanelLayout={defaultPanelLayout}
                        onSetDefaultPanelLayout={handleSetDefaultPanelLayout}
                        defaultImageCount={defaultImageCount}
                        onSetDefaultImageCount={handleSetDefaultImageCount}
                        onGenerateAllStoryboards={handleGenerateAllStoryboards}
                        isGeneratingStoryboards={isGeneratingStoryboards}
                        onGenerateAllCharacters={handleGenerateAllCharacters}
                        isGeneratingCharacters={isGeneratingCharacters}
                        onGenerateAllScenes={handleGenerateAllScenes}
                        isGeneratingScenes={isGeneratingScenes}
                    />
                        <div className="flex-1 overflow-y-auto pb-20 custom-scrollbar">
                            {shots.map((shot, index) => (
                                <ShotItem 
                                    key={shot.id} 
                                    shot={shot} 
                                    index={index}
                                    projectId={projectId}
                                    defaultImageCount={defaultImageCount}
                                    onDelete={handleDelete}
                                    onUpdate={handleUpdate}
                                    onGenerate={handleGenerate}
                                    onDeleteShotImage={handleDeleteShotImage}
                                    onDeleteVideo={handleDeleteShotVideo}
                                    onMoveUp={() => handleMoveUp(index)}
                                    onMoveDown={() => handleMoveDown(index)}
                                    allCharacters={characters}
                                    onCharacterClick={onCharacterClick}
                                    allScenes={scenes}
                                    onSceneClick={onSceneClick}
                                    onShotImageClick={onShotImageClick}
                                    onSelectCandidate={handleSelectShotCandidate}
                                    isSelected={selectedShots.has(shot.id)}
                                    onSelect={(selected) => handleSelectShot(shot.id, selected)}
                                />
                            ))}
                            <div className="p-4">
                                <button 
                                    onClick={handleAddShot}
                                    className="w-full py-4 border-2 border-dashed border-dark-700 rounded-lg text-gray-500 hover:border-accent hover:text-accent flex items-center justify-center gap-2 transition-all hover:bg-dark-800"
                                >
                                    <Plus size={20}/> 添加新镜头
                                </button>
                            </div>
                        </div>
                    </div>
                </main>
                <Sidebar 
                    characters={characters} 
                    scenes={scenes} 
                    onCharacterClick={onCharacterClick}
                    onSceneClick={onSceneClick}
                    onAddCharacter={handleAddCharacterClick}
                    onAddScene={handleAddSceneClick}
                    onGenerateCharacter={() => handleOpenGenerateModal('character')}
                    onGenerateScene={() => handleOpenGenerateModal('scene')}
                    onRegenerateCharacter={(char) => handleOpenGenerateModal('character', char)}
                    onRegenerateScene={(scene) => handleOpenGenerateModal('scene', scene)}
                    onDeleteCharacter={async (charId) => {
                        if (!confirm('确定删除该角色？')) return;
                        const prevChars = [...characters];
                        const prevShots = [...shots];
                        setCharacters(prev => prev.filter(c => c.id !== charId));
                        setShots(prev => prev.map(s => ({ ...s, characters: (s.characters || []).filter(id => id !== charId) })));
                        try {
                            await ApiService.deleteCharacter(projectId, charId);
                        } catch (e) {
                            alert('删除角色失败');
                            setCharacters(prevChars);
                            setShots(prevShots);
                        }
                    }}
                    onGenerateAllCharacters={handleGenerateAllCharacters}
                    onGenerateAllScenes={handleGenerateAllScenes}
                    isGeneratingCharacters={isGeneratingCharacters}
                    isGeneratingScenes={isGeneratingScenes}
                    defaultSceneId={defaultSceneId}
                    onSetDefaultScene={handleSetDefaultScene}
                />
            </div>
            <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                accept="image/*" 
                onChange={handleFileChange}
            />
            <input 
                type="file" 
                ref={sceneFileInputRef} 
                className="hidden" 
                accept="image/*" 
                onChange={handleSceneFileChange}
            />
            <input 
                type="file" 
                ref={shotFileInputRef} 
                className="hidden" 
                accept="image/*" 
                onChange={handleShotFileChange}
            />
            <input
                type="file"
                ref={importFileInputRef}
                className="hidden"
                accept="application/json"
                onChange={async (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    try {
                        const text = await file.text();
                        const data = JSON.parse(text);
                        const name = prompt("导入为新项目的名称", data?.meta?.name || "导入项目");
                        if (!name) return;
                        const created = await ApiService.createProject(name, (data?.meta?.style || 'anime'));
                        setProjects(prev => [created, ...prev]);
                        navigate(`/project/${created.id}`);
                        
                        const charIdMap = {};
                        for (const c of data.characters || []) {
                            const newChar = { ...c, id: `char_${Date.now()}_${Math.random().toString(36).slice(2, 9)}` };
                            await ApiService.createCharacter(created.id, newChar);
                            charIdMap[c.id] = newChar.id;
                        }
                        const sceneIdMap = {};
                        for (const s of data.scenes || []) {
                            const newScene = { ...s, id: `scene_${Date.now()}_${Math.random().toString(36).slice(2, 9)}` };
                            await ApiService.createScene(created.id, newScene);
                            sceneIdMap[s.id] = newScene.id;
                        }
                        for (const shot of data.shots || []) {
                            const newShot = {
                                prompt: shot.prompt || "",
                                dialogue: shot.dialogue || "",
                                characters: (shot.characters || []).map(cid => charIdMap[cid]).filter(Boolean),
                                scene_id: shot.scene_id ? sceneIdMap[shot.scene_id] : null,
                                image_url: shot.image_url || "",
                                video_url: shot.video_url || ""
                            };
                            await ApiService.createShot(created.id, newShot);
                        }
                    } catch (err) {
                        alert("导入失败");
                    }
                    e.target.value = null;
                }}
            />
            <input 
                type="file" 
                ref={newCharFileInputRef} 
                className="hidden" 
                accept="image/*" 
                onChange={handleNewCharacterFileChange}
            />
            <input 
                type="file" 
                ref={newSceneFileInputRef} 
                className="hidden" 
                accept="image/*" 
                onChange={handleNewSceneFileChange}
            />
            <AddScriptModal 
                isOpen={isScriptModalOpen} 
                onClose={() => setIsScriptModalOpen(false)} 
                onSubmit={handleParseScript}
            />
            <GenerateAssetModal 
                isOpen={isGenerateModalOpen} 
                onClose={() => setIsGenerateModalOpen(false)} 
                onSubmit={handleGenerateAsset}
                type={generateType}
                initialName={regenerateAssetData?.name || ''}
                initialPrompt={regenerateAssetData?.prompt || ''}
            />
            <ApiConfigModal 
                isOpen={isApiConfigOpen} 
                onClose={() => setIsApiConfigOpen(false)} 
            />
        </div>
    );
};

export default ProjectEditor;
