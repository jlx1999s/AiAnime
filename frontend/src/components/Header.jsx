import React from 'react';
import { ChevronDown, History, Settings, User } from 'lucide-react';

const Header = () => (
    <header className="h-14 border-b border-dark-700 flex items-center justify-between px-4 bg-dark-800 flex-shrink-0">
        <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
                <span className="text-accent">MochiAni</span>
                <span className="text-sm font-normal text-gray-400">| 守墓五年，我携万剑归...</span>
            </h1>
            <div className="flex gap-2">
                <button className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 flex items-center gap-1">
                    风格: 日漫 <ChevronDown size={12}/>
                </button>
                <button className="px-3 py-1 text-xs bg-dark-700 text-gray-300 rounded hover:bg-dark-600 flex items-center gap-1">
                    模型配置 <ChevronDown size={12}/>
                </button>
            </div>
        </div>
        <div className="flex items-center gap-3 text-gray-400">
            <button className="hover:text-white flex items-center gap-1 text-sm"><History size={16}/> 生成记录</button>
        </div>
    </header>
);

export default Header;
