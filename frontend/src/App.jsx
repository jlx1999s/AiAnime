import React, { useState, useEffect } from 'react';
import { Plus, Film } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ShotListHeader from './components/ShotListHeader';
import ShotItem from './components/ShotItem';
import { ApiService } from './services/api';

const App = () => {
    const [shots, setShots] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [loading, setLoading] = useState(true);
    const projectId = "default_project";

    // Load initial data
    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const project = await ApiService.getProject(projectId);
                setShots(project.shots);
                setCharacters(project.characters);
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
                <Sidebar characters={characters}/>
            </div>
        </div>
    );
};

export default App;
