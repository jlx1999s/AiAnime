import React, { useState, useEffect } from 'react';
import { Plus, Film } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ShotListHeader from './components/ShotListHeader';
import ShotItem from './components/ShotItem';
import AddScriptModal from './components/AddScriptModal';
import GenerateAssetModal from './components/GenerateAssetModal';
import { ApiService } from './services/api';

const App = () => {
    const [shots, setShots] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isScriptModalOpen, setIsScriptModalOpen] = useState(false);
    const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
    const [generateType, setGenerateType] = useState('character'); // 'character' or 'scene'
    const [selectedCharId, setSelectedCharId] = useState(null);
    const [selectedSceneId, setSelectedSceneId] = useState(null);
    const [selectedShotId, setSelectedShotId] = useState(null);
    const [projects, setProjects] = useState([]);
    const [projectId, setProjectId] = useState(null);
    const fileInputRef = React.useRef(null);
    const sceneFileInputRef = React.useRef(null);
    const shotFileInputRef = React.useRef(null);
    const newCharFileInputRef = React.useRef(null);
    const newSceneFileInputRef = React.useRef(null);
    const importFileInputRef = React.useRef(null);
    const loadProjects = async () => {
        try {
            setLoading(true);
            const list = await ApiService.getProjects();
            setProjects(list);
            const initialId = list[0]?.id;
            if (initialId) {
                setProjectId(initialId);
            } else {
                try {
                    const created = await ApiService.createProject('新项目');
                    setProjects([created]);
                    setProjectId(created.id);
                } catch (err) {
                    console.error("Failed to create default project", err);
                }
            }
        } catch (e) {
            console.error("Failed to load projects", e);
        } finally {
            // 防止因未选中项目而一直停留在加载态
            setLoading(false);
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
                setShots(project.shots || []);
                setCharacters(project.characters || []);
                setScenes(project.scenes || []);
            } catch (error) {
                console.error("Failed to load project", error);
            }
            setLoading(false);
        };
        loadData();
    }, [projectId]);

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

    const handleAddShot = async () => {
        const tempId = Date.now();
        const newShotData = {
            prompt: "",
            dialogue: "",
            characters: [],
            scene: null,
        };
        
        // Optimistic UI
        const optimisitcShot = {
             id: tempId, 
             ...newShotData, 
             image_url: "https://placehold.co/300x169/25262b/FFF?text=Loading..." 
        };
        setShots([...shots, optimisitcShot]);

        try {
            const createdShot = await ApiService.createShot(projectId, newShotData);
            // Replace temp ID with real one
            setShots(prev => prev.map(s => s.id === tempId ? createdShot : s));
        } catch (e) {
            console.error("Create failed", e);
        }
    };

    const handleGenerate = async (shotId, type, count) => {
         alert(`正在请求后端生成 ${type}...`);
         setShots(prev => prev.map(s => s.id === shotId ? { ...s, status: 'generating' } : s));
         await ApiService.generate(projectId, shotId, type, count);

         const startedAt = Date.now();
         const timeoutMs = type === 'video' ? 5 * 60 * 1000 : 2 * 60 * 1000;

         while (Date.now() - startedAt < timeoutMs) {
             try {
                 const project = await ApiService.getProject(projectId);
                 const nextShot = (project.shots || []).find(s => s.id === shotId);
                 if (nextShot) {
                     setShots(prev => prev.map(s => s.id === shotId ? nextShot : s));
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
            const newShots = await ApiService.parseScript(content);
            
            // 1. Extract unique character names
            const allNames = new Set();
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
                    const newChar = {
                        id: `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name.trim(),
                        avatar_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${name}`,
                        tags: []
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
                    const newScene = {
                        id: `scene_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name.trim(),
                        image_url: "", // Placeholder
                        tags: []
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

                const shotToCreate = { 
                    ...shotData, 
                    characters: charIds,
                    scene_id: sceneId 
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
            const url = await ApiService.uploadFile(file);
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
            const url = await ApiService.uploadFile(file);
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
            const url = await ApiService.uploadFile(file);
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
            setShots(prev => prev.map(s => s.id === shotId ? updated : s));
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
            const url = await ApiService.uploadFile(file);
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

    const handleOpenGenerateModal = (type) => {
        setGenerateType(type);
        setIsGenerateModalOpen(true);
    };

    const handleGenerateAsset = async (name, prompt, type) => {
        try {
            // 1. Call Generation API
            const result = await ApiService.generateAsset(prompt, type);
            const url = result.url;
            
            // 2. Create Asset
            if (type === 'character') {
                const newChar = {
                    id: `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                    name: name,
                    avatar_url: url,
                    tags: []
                };
                await ApiService.createCharacter(projectId, newChar);
                setCharacters(prev => [...prev, newChar]);
            } else if (type === 'scene') {
                const newScene = {
                    id: `scene_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                    name: name,
                    image_url: url,
                    tags: []
                };
                await ApiService.createScene(projectId, newScene);
                setScenes(prev => [...prev, newScene]);
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
            <Header 
                projects={projects} 
                currentProjectId={projectId} 
                onChangeProject={(id) => setProjectId(id)}
                onCreateProject={async () => {
                    const name = prompt("请输入新项目名称");
                    if (!name) return;
                    const created = await ApiService.createProject(name);
                    setProjects(prev => [created, ...prev]);
                    setProjectId(created.id);
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
                    setProjects(prev => prev.filter(p => p.id !== projectId));
                    const next = projects.find(p => p.id !== projectId);
                    if (next) {
                        setProjectId(next.id);
                    } else {
                        const created = await ApiService.createProject('新项目');
                        setProjects([created]);
                        setProjectId(created.id);
                    }
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
                    setProjectId(created.id);
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
                    const refreshed = await ApiService.getProject(created.id);
                    setShots(refreshed.shots || []);
                    setCharacters(refreshed.characters || []);
                    setScenes(refreshed.scenes || []);
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
                        <button className="hover:text-white flex items-center gap-1 transition-colors ml-auto text-accent">
                            <Film size={12}/> 导出视频
                        </button>
                    </div>

                    {/* Shot List Header & Content */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <ShotListHeader />
                        <div className="flex-1 overflow-y-auto pb-20 custom-scrollbar">
                            {shots.map((shot, index) => (
                                <ShotItem 
                                    key={shot.id} 
                                    shot={shot} 
                                    index={index}
                                    onDelete={handleDelete}
                                    onUpdate={handleUpdate}
                                    onGenerate={handleGenerate}
                                    allCharacters={characters}
                                    onCharacterClick={onCharacterClick}
                                    allScenes={scenes}
                                    onSceneClick={onSceneClick}
                                    onShotImageClick={onShotImageClick}
                                    onSelectCandidate={handleSelectShotCandidate}
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
                    onSceneClick={onSceneClick}
                    onAddCharacter={handleAddCharacterClick}
                    onAddScene={handleAddSceneClick}
                    onGenerateCharacter={() => handleOpenGenerateModal('character')}
                    onGenerateScene={() => handleOpenGenerateModal('scene')}
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
                        setProjectId(created.id);
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
                        const refreshed = await ApiService.getProject(created.id);
                        setShots(refreshed.shots || []);
                        setCharacters(refreshed.characters || []);
                        setScenes(refreshed.scenes || []);
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
            />
        </div>
    );
};

export default App;
