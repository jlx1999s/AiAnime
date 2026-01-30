import React from 'react';
import { Wand2, RefreshCw } from 'lucide-react';

const ShotListHeader = ({ allSelected, onSelectAll, defaultPanelLayout, onSetDefaultPanelLayout, defaultImageCount, onSetDefaultImageCount, onGenerateAllStoryboards, isGeneratingStoryboards, onGenerateAllCharacters, isGeneratingCharacters, onGenerateAllScenes, isGeneratingScenes }) => (
    <div className="grid grid-cols-[40px_minmax(260px,2fr)_minmax(180px,1.2fr)_minmax(180px,1.2fr)_minmax(180px,1.2fr)_minmax(240px,1.6fr)_minmax(240px,1.6fr)_40px] gap-4 px-4 py-2 bg-dark-800 border-b border-dark-700 text-xs font-bold text-gray-500 uppercase tracking-wider sticky top-0 z-10 shadow-sm">
        <div className="flex items-center justify-center">
            <input 
                type="checkbox" 
                className="rounded bg-dark-700 border-dark-600 w-4 h-4 cursor-pointer accent-accent"
                checked={allSelected || false}
                onChange={(e) => onSelectAll && onSelectAll(e.target.checked)}
                title="全选/取消全选"
            />
        </div>
        <div>调整剧本</div>
        <div className="flex items-center justify-between">
            <span>出场人物</span>
            <button
                onClick={onGenerateAllCharacters}
                disabled={isGeneratingCharacters}
                className={`text-[10px] px-2 py-0.5 rounded transition-colors flex items-center gap-1 ${isGeneratingCharacters ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-dark-700 hover:bg-accent text-gray-300 hover:text-white'}`}
                title="为所有角色生成图片（仅未生成的）"
            >
                {isGeneratingCharacters ? <RefreshCw size={10} className="animate-spin"/> : <Wand2 size={10} />} 
                {isGeneratingCharacters ? '生成中...' : '一键生成'}
            </button>
        </div>
        <div className="flex items-center justify-between">
            <span>场景</span>
            <button
                onClick={onGenerateAllScenes}
                disabled={isGeneratingScenes}
                className={`text-[10px] px-2 py-0.5 rounded transition-colors flex items-center gap-1 ${isGeneratingScenes ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-dark-700 hover:bg-accent text-gray-300 hover:text-white'}`}
                title="为所有场景生成图片（仅未生成的）"
            >
                {isGeneratingScenes ? <RefreshCw size={10} className="animate-spin"/> : <Wand2 size={10} />} 
                {isGeneratingScenes ? '生成中...' : '一键生成'}
            </button>
        </div>
        <div>自定义参考图</div>
        <div className="flex items-center gap-2">
            <span>分镜</span>
            <div className="flex items-center gap-1 ml-auto">
                <button
                    onClick={onGenerateAllStoryboards}
                    disabled={isGeneratingStoryboards}
                    className={`text-[10px] px-2 py-0.5 rounded transition-colors flex items-center gap-1 ${isGeneratingStoryboards ? 'bg-dark-700 text-gray-600 cursor-not-allowed' : 'bg-dark-700 hover:bg-accent text-gray-300 hover:text-white'}`}
                    title="为所有分镜生成图片（仅未生成的）"
                >
                    {isGeneratingStoryboards ? <RefreshCw size={10} className="animate-spin"/> : <Wand2 size={10} />} 
                    {isGeneratingStoryboards ? '生成中...' : '一键生成'}
                </button>
                <select 
                    className="bg-dark-700 text-[10px] text-gray-300 rounded border border-dark-600 focus:border-accent outline-none px-1 py-0.5"
                    value={defaultPanelLayout || '3-panel'}
                    onChange={(e) => onSetDefaultPanelLayout && onSetDefaultPanelLayout(e.target.value)}
                    title="默认分镜布局"
                >
                    <option value="1-panel">单图</option>
                    <option value="2-panel">二宫格</option>
                    <option value="3-panel">三宫格</option>
                    <option value="4-panel">四宫格</option>
                </select>
                <input 
                    type="number" 
                    min="1" 
                    max="4" 
                    className="w-8 bg-dark-700 text-[10px] text-gray-300 rounded border border-dark-600 focus:border-accent outline-none px-1 py-0.5 text-center"
                    value={defaultImageCount || 4}
                    onChange={(e) => onSetDefaultImageCount && onSetDefaultImageCount(e.target.value)}
                    title="默认生成张数"
                />
            </div>
        </div>
        <div>视频</div>
        <div className="text-center">操作</div>
    </div>
);

export default ShotListHeader;
