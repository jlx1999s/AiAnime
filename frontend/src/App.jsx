import React, { useState, useEffect } from 'react';
import { Plus, Film } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ShotListHeader from './components/ShotListHeader';
import ShotItem from './components/ShotItem';
import AddScriptModal from './components/AddScriptModal';
import { ApiService } from './services/api';

const App = () => {
    const [shots, setShots] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isScriptModalOpen, setIsScriptModalOpen] = useState(false);
    const [selectedCharId, setSelectedCharId] = useState(null);
    const [selectedSceneId, setSelectedSceneId] = useState(null);
    const [selectedShotId, setSelectedShotId] = useState(null);
    const fileInputRef = React.useRef(null);
    const sceneFileInputRef = React.useRef(null);
    const shotFileInputRef = React.useRef(null);
    const projectId = "default_project";

    // Load initial data
    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const project = await ApiService.getProject(projectId);
                setShots(project.shots);
                setCharacters(project.characters);
                setScenes(project.scenes || []);
            } catch (error) {
                console.error("Failed to load project", error);
            }
            setLoading(false);
        };
        loadData();
    }, []);

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

    const handleGenerate = async (shotId, type) => {
         // Trigger generation
         alert(`正在请求后端生成 ${type}...`);
         await ApiService.generate(shotId, type);
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
            const charMap = {}; // Name -> ID
            const currentChars = [...characters];
            
            // Map existing characters first
            currentChars.forEach(c => charMap[c.name] = c.id);

            // Create new characters for unknown names
            const newCharsToCreate = [];
            for (const name of allNames) {
                if (!charMap[name]) {
                    const newChar = {
                        id: `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name,
                        avatar_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${name}`,
                        tags: []
                    };
                    newCharsToCreate.push(newChar);
                    charMap[name] = newChar.id; // Assign temp ID
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

            const sceneMap = {}; // Name -> ID
            const currentScenes = [...scenes];
            currentScenes.forEach(s => sceneMap[s.name] = s.id);

            const newScenesToCreate = [];
            for (const name of allScenes) {
                if (!sceneMap[name]) {
                    const newScene = {
                        id: `scene_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        name: name,
                        image_url: "", // Placeholder
                        tags: []
                    };
                    newScenesToCreate.push(newScene);
                    sceneMap[name] = newScene.id;
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
                const charIds = (shotData.characters || []).map(name => charMap[name]).filter(Boolean);
                const sceneId = shotData.scene ? sceneMap[shotData.scene] : null;

                const shotToCreate = { 
                    ...shotData, 
                    characters: charIds,
                    scene_id: sceneId 
                };
                
                const created = await ApiService.createShot(projectId, shotToCreate);
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

    if (loading) {
        return <div className="h-screen flex items-center justify-center bg-dark-900 text-gray-500">加载项目中...</div>;
    }

    return (
        <div className="flex flex-col h-screen overflow-hidden font-sans">
            <Header />
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
                <Sidebar characters={characters} scenes={scenes} onSceneClick={onSceneClick}/>
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
            <AddScriptModal 
                isOpen={isScriptModalOpen} 
                onClose={() => setIsScriptModalOpen(false)} 
                onSubmit={handleParseScript}
            />
        </div>
    );
};

export default App;
