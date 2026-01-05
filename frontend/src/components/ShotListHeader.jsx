import React from 'react';

const ShotListHeader = () => (
    <div className="grid grid-cols-[40px_minmax(300px,2fr)_1fr_1fr_1.5fr_40px] gap-4 px-4 py-2 bg-dark-800 border-b border-dark-700 text-xs font-bold text-gray-500 uppercase tracking-wider sticky top-0 z-10 shadow-sm">
        <div className="text-center">序号</div>
        <div>剧本</div>
        <div>出场人物</div>
        <div>场景</div>
        <div>视频</div>
        <div className="text-center">操作</div>
    </div>
);

export default ShotListHeader;
