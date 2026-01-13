import React from 'react';
import { ChevronDown, History } from 'lucide-react';

const Header = ({ projects = [], currentProjectId, onChangeProject, onCreateProject, onRenameProject, onDeleteProject, onChangeStyle, onDuplicateProject, onExportProject, onImportProject }) => {
    const current = projects.find(p => p.id === currentProjectId);
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
                        <option value="manga">漫画</option>
                        <option value="realistic">写实</option>
                    </select>
                </div>
            </div>
            <div className="flex items-center gap-3 text-gray-400">
                <button className="hover:text-white flex items-center gap-1 text-sm"><History size={16}/> 生成记录</button>
            </div>
        </header>
    );
};

export default Header;
