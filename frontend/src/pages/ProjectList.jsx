import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiService } from '../services/api';
import { Plus, Trash2, FolderOpen, Film } from 'lucide-react';

const ProjectList = () => {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const loadProjects = async () => {
        try {
            setLoading(true);
            const list = await ApiService.getProjects();
            setProjects(list);
        } catch (e) {
            console.error("Failed to load projects", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadProjects();
    }, []);

    const handleCreateProject = async () => {
        const name = prompt("请输入新项目名称");
        if (!name) return;
        try {
            const created = await ApiService.createProject(name);
            setProjects([created, ...projects]);
            navigate(`/project/${created.id}`);
        } catch (e) {
            console.error("Failed to create project", e);
            alert("创建项目失败");
        }
    };

    const handleDeleteProject = async (e, projectId) => {
        e.stopPropagation();
        if (!confirm("确定删除该项目？该操作不可恢复")) return;
        try {
            await ApiService.deleteProject(projectId);
            setProjects(projects.filter(p => p.id !== projectId));
        } catch (e) {
            console.error("Failed to delete project", e);
            alert("删除项目失败");
        }
    };

    if (loading) {
        return <div className="h-screen flex items-center justify-center bg-dark-900 text-gray-500">加载中...</div>;
    }

    return (
        <div className="min-h-screen bg-dark-900 text-gray-300 p-8 font-sans">
            <div className="max-w-6xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Film className="text-accent" />
                        漫剧项目管理
                    </h1>
                    <button 
                        onClick={handleCreateProject}
                        className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                    >
                        <Plus size={18} />
                        新建项目
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {/* Create New Card */}
                    <div 
                        onClick={handleCreateProject}
                        className="bg-dark-800 border-2 border-dashed border-dark-700 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer hover:border-accent hover:bg-dark-750 transition-all h-48 group"
                    >
                        <div className="w-12 h-12 rounded-full bg-dark-700 flex items-center justify-center mb-3 group-hover:bg-accent group-hover:text-white transition-colors">
                            <Plus size={24} />
                        </div>
                        <span className="text-gray-400 font-medium group-hover:text-white">创建新项目</span>
                    </div>

                    {/* Project Cards */}
                    {projects.map(project => (
                        <div 
                            key={project.id}
                            onClick={() => navigate(`/project/${project.id}`)}
                            className="bg-dark-800 border border-dark-700 rounded-xl overflow-hidden hover:border-gray-500 hover:shadow-lg transition-all cursor-pointer group flex flex-col h-48 relative"
                        >
                            <div className="p-5 flex-1 flex flex-col">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="bg-dark-700 p-2 rounded-lg">
                                        <FolderOpen size={20} className="text-accent" />
                                    </div>
                                    <button 
                                        onClick={(e) => handleDeleteProject(e, project.id)}
                                        className="text-gray-600 hover:text-red-500 p-1 rounded hover:bg-dark-700 transition-colors opacity-0 group-hover:opacity-100"
                                        title="删除项目"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-1 truncate" title={project.name}>
                                    {project.name}
                                </h3>
                                <div className="text-xs text-gray-500 mt-auto">
                                    <p>ID: {project.id.slice(0, 8)}...</p>
                                    <p className="mt-1">风格: {project.style || '默认'}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ProjectList;
