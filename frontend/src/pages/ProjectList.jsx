import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiService } from '../services/api';
import { Plus, Trash2, FolderOpen, Film } from 'lucide-react';

const ProjectList = () => {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState(ApiService.getCurrentUser());
    const [authMode, setAuthMode] = useState('login');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [users, setUsers] = useState([]);
    const [projectQuery, setProjectQuery] = useState('');
    const [ownerFilter, setOwnerFilter] = useState('all');
    const [selectedProjects, setSelectedProjects] = useState(new Set());
    const [bulkOwnerId, setBulkOwnerId] = useState('');
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
        if (user) {
            loadProjects();
            if (user.is_admin) {
                ApiService.adminListUsers().then(setUsers).catch(() => setUsers([]));
            } else {
                setUsers([]);
            }
        } else {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        setSelectedProjects(prev => new Set([...prev].filter(id => projects.some(p => p.id === id))));
    }, [projects]);

    const handleAuth = async () => {
        if (!username || !password) {
            alert("请输入用户名和密码");
            return;
        }
        try {
            const result = authMode === 'register'
                ? await ApiService.register(username, password)
                : await ApiService.login(username, password);
            ApiService.setCurrentUser(result);
            setUser(result);
            setUsername('');
            setPassword('');
        } catch (e) {
            alert(e.message || "操作失败");
        }
    };

    const handleLogout = async () => {
        try {
            await ApiService.logout();
        } catch {
        }
        ApiService.clearCurrentUser();
        setUser(null);
        setProjects([]);
    };

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

    if (!user) {
        return (
            <div className="min-h-screen bg-dark-900 text-gray-300 p-8 font-sans">
                <div className="max-w-md mx-auto bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl shadow-black/20">
                    <h1 className="text-xl font-bold text-white mb-4">用户登录</h1>
                    <div className="space-y-3">
                        <input
                            className="w-full bg-dark-900 border border-dark-700 rounded p-2 text-sm text-gray-300 focus:border-accent focus:outline-none"
                            placeholder="用户名"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                        />
                        <input
                            type="password"
                            className="w-full bg-dark-900 border border-dark-700 rounded p-2 text-sm text-gray-300 focus:border-accent focus:outline-none"
                            placeholder="密码"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleAuth}
                                className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded-lg transition-colors"
                            >
                                {authMode === 'register' ? '注册' : '登录'}
                            </button>
                            <button
                                onClick={() => setAuthMode(authMode === 'register' ? 'login' : 'register')}
                                className="text-gray-400 hover:text-white text-sm"
                            >
                                {authMode === 'register' ? '切换到登录' : '切换到注册'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const getOwnerName = (ownerId) => {
        if (!ownerId) return "未分配";
        return users.find(u => u.id === ownerId)?.username || ownerId;
    };

    const normalize = (value) => (value || '').toString().trim().toLowerCase();
    const filteredProjects = user.is_admin
        ? projects.filter(p => {
            const matchName = !projectQuery || normalize(p.name).includes(normalize(projectQuery));
            if (!matchName) return false;
            if (ownerFilter === 'all') return true;
            if (ownerFilter === 'unassigned') return !p.owner_id;
            return p.owner_id === ownerFilter;
        })
        : projects;

    const toggleSelectProject = (projectId) => {
        setSelectedProjects(prev => {
            const next = new Set(prev);
            if (next.has(projectId)) {
                next.delete(projectId);
            } else {
                next.add(projectId);
            }
            return next;
        });
    };

    const handleSelectAllFiltered = () => {
        setSelectedProjects(new Set(filteredProjects.map(p => p.id)));
    };

    const handleClearSelected = () => {
        setSelectedProjects(new Set());
    };

    const handleBulkAssign = async () => {
        if (selectedProjects.size === 0) {
            alert("请先选择项目");
            return;
        }
        try {
            const updated = await ApiService.adminAssignProjectsBulk([...selectedProjects], bulkOwnerId || null);
            const updatedMap = new Map(updated.map(p => [p.id, p]));
            setProjects(prev => prev.map(p => updatedMap.get(p.id) || p));
            setSelectedProjects(new Set());
        } catch (e) {
            alert(e.message || "批量分配失败");
        }
    };

    return (
        <div className="min-h-screen bg-dark-900 text-gray-300 px-6 py-8 font-sans">
            <div className="max-w-6xl mx-auto space-y-6">
                <div className="flex flex-wrap justify-between items-center gap-4">
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Film className="text-accent" />
                        漫剧项目管理
                    </h1>
                    <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-300 bg-dark-800 border border-dark-700 px-3 py-1.5 rounded-full">
                            {user.username}
                        </span>
                        <a
                            href="http://localhost:8501"
                            target="_blank"
                            rel="noreferrer"
                            className="text-gray-300 bg-dark-800 border border-dark-700 px-3 py-1.5 rounded-lg text-sm hover:border-accent hover:text-white transition-colors"
                        >
                            漫剧剧本管理
                        </a>
                        <button
                            onClick={handleLogout}
                            className="text-gray-400 hover:text-white text-sm"
                        >
                            退出
                        </button>
                        <button 
                            onClick={handleCreateProject}
                            className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-accent/20"
                        >
                            <Plus size={18} />
                            新建项目
                        </button>
                    </div>
                </div>

                {user.is_admin && (
                    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 flex flex-wrap gap-3 items-center shadow-lg shadow-black/20">
                        <input
                            className="bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:border-accent focus:outline-none flex-1 min-w-[180px]"
                            placeholder="搜索项目名称"
                            value={projectQuery}
                            onChange={(e) => setProjectQuery(e.target.value)}
                        />
                        <select
                            className="bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none focus:border-accent"
                            value={ownerFilter}
                            onChange={(e) => setOwnerFilter(e.target.value)}
                        >
                            <option value="all">全部归属</option>
                            <option value="unassigned">未分配</option>
                            {users.map(u => (
                                <option key={u.id} value={u.id}>{u.username}</option>
                            ))}
                        </select>
                        <select
                            className="bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none focus:border-accent"
                            value={bulkOwnerId}
                            onChange={(e) => setBulkOwnerId(e.target.value)}
                        >
                            <option value="">分配为未分配</option>
                            {users.map(u => (
                                <option key={u.id} value={u.id}>{u.username}</option>
                            ))}
                        </select>
                        <button
                            onClick={handleBulkAssign}
                            className="bg-accent hover:bg-accent-hover text-white px-3 py-2 rounded-lg text-sm shadow-lg shadow-accent/20"
                        >
                            批量分配
                        </button>
                        <button
                            onClick={handleSelectAllFiltered}
                            className="text-gray-400 hover:text-white text-sm"
                        >
                            全选当前
                        </button>
                        <button
                            onClick={handleClearSelected}
                            className="text-gray-400 hover:text-white text-sm"
                        >
                            清空选择
                        </button>
                        <span className="text-xs text-gray-500">已选 {selectedProjects.size}</span>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    <div 
                        onClick={handleCreateProject}
                        className="bg-dark-800 border-2 border-dashed border-dark-700 rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer hover:border-accent hover:bg-dark-750 transition-all h-52 group shadow-lg shadow-black/20"
                    >
                        <div className="w-12 h-12 rounded-full bg-dark-700 flex items-center justify-center mb-3 group-hover:bg-accent group-hover:text-white transition-colors">
                            <Plus size={24} />
                        </div>
                        <span className="text-gray-400 font-medium group-hover:text-white">创建新项目</span>
                    </div>

                    {filteredProjects.map(project => {
                        const isSelected = selectedProjects.has(project.id);
                        return (
                        <div 
                            key={project.id}
                            onClick={() => toggleSelectProject(project.id)}
                            className={`bg-dark-800 border rounded-2xl overflow-hidden hover:border-gray-500 hover:shadow-xl transition-all duration-200 cursor-pointer group flex flex-col h-52 relative shadow-lg shadow-black/20 hover:-translate-y-1 ${isSelected ? 'border-accent ring-1 ring-accent/60' : 'border-dark-700'}`}
                        >
                            <div className="p-5 flex-1 flex flex-col gap-3">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-start gap-3">
                                        <div className="bg-dark-700 p-2 rounded-lg">
                                            <FolderOpen size={20} className="text-accent" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-lg font-semibold text-white truncate" title={project.name}>
                                                {project.name}
                                            </h3>
                                            <div className="mt-1 flex items-center gap-2">
                                                <span className="text-[11px] text-gray-400">ID {project.id.slice(0, 8)}...</span>
                                                <span className="text-[11px] text-gray-500">风格 {project.style || '默认'}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={(e) => handleDeleteProject(e, project.id)}
                                        className="text-gray-600 hover:text-red-500 p-1 rounded hover:bg-dark-700 transition-colors opacity-0 group-hover:opacity-100"
                                        title="删除项目"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                                <div className="mt-auto">
                                    <div className="flex items-center gap-2">
                                        <span className={`text-[11px] px-2 py-0.5 rounded-full border ${project.owner_id ? 'text-emerald-300 border-emerald-600/40 bg-emerald-500/10' : 'text-amber-300 border-amber-600/40 bg-amber-500/10'}`}>
                                            {project.owner_id ? '已分配' : '未分配'}
                                        </span>
                                        {user.is_admin && (
                                            <span className="text-[11px] text-gray-400">归属 {getOwnerName(project.owner_id)}</span>
                                        )}
                                    </div>
                                    <div className="mt-3 flex items-center justify-between gap-2">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                navigate(`/project/${project.id}`);
                                            }}
                                            className="text-xs text-gray-300 bg-dark-900 border border-dark-700 px-3 py-1.5 rounded-lg hover:border-accent hover:text-white transition-colors"
                                        >
                                            查看项目
                                        </button>
                                    </div>
                                    {user.is_admin && (
                                        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
                                            <div className="relative">
                                                <select
                                                    className="w-full bg-dark-900 border border-dark-700 rounded-lg text-sm text-gray-300 px-3 py-2 outline-none focus:border-accent appearance-none"
                                                    value={project.owner_id || ""}
                                                    onChange={async (e) => {
                                                        const nextOwner = e.target.value || null;
                                                        try {
                                                            const updated = await ApiService.adminAssignProject(project.id, nextOwner);
                                                            setProjects(prev => prev.map(p => p.id === project.id ? updated : p));
                                                        } catch (err) {
                                                            alert(err.message || "分配失败");
                                                        }
                                                    }}
                                                >
                                                    <option value="">未分配</option>
                                                    {users.map(u => (
                                                        <option key={u.id} value={u.id}>{u.username}</option>
                                                    ))}
                                                </select>
                                                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none">▾</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default ProjectList;
