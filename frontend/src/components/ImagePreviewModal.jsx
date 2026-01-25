import React from 'react';
import { X, Download } from 'lucide-react';

const ImagePreviewModal = ({ isOpen, onClose, imageUrl, title }) => {
    if (!isOpen || !imageUrl) return null;

    const handleDownload = async () => {
        try {
            const response = await fetch(imageUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `image-${Date.now()}.png`; // Default filename
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Download failed:', error);
            // Fallback for direct links (cross-origin might fail fetch)
            const a = document.createElement('a');
            a.href = imageUrl;
            a.download = `image-${Date.now()}.png`;
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
            <div className="relative max-w-[95vw] max-h-[95vh] flex flex-col items-center" onClick={e => e.stopPropagation()}>
                {/* Header Actions */}
                <div className="absolute top-4 right-4 flex gap-2 z-10">
                    <button 
                        onClick={handleDownload}
                        className="p-2 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
                        title="下载图片"
                    >
                        <Download size={20} />
                    </button>
                    <button 
                        onClick={onClose}
                        className="p-2 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
                        title="关闭预览"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Image */}
                <img 
                    src={imageUrl} 
                    alt={title || "Preview"} 
                    className="max-w-full max-h-[90vh] object-contain rounded shadow-2xl"
                />
                
                {title && (
                    <div className="mt-2 text-white text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
                        {title}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ImagePreviewModal;
