import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ProjectList from './pages/ProjectList';
import ProjectEditor from './pages/ProjectEditor';
import AssetManager from './pages/AssetManager';

const App = () => {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<ProjectList />} />
                <Route path="/project/:projectId" element={<ProjectEditor />} />
                <Route path="/project/:projectId/assets" element={<AssetManager />} />
            </Routes>
        </Router>
    );
};

export default App;
