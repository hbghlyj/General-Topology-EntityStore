import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomeGraphPage from './pages/HomeGraphPage';
import ExplorerPage from './pages/ExplorerPage';
import EntityDetailPage from './pages/EntityDetailPage';
import AboutPage from './pages/AboutPage';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Navbar />
      <main className="flex-1 flex flex-col">
        <Routes>
          <Route path="/" element={<HomeGraphPage />} />
          <Route path="/explorer" element={<ExplorerPage />} />
          <Route path="/entity/:id" element={<EntityDetailPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/explorer" replace />} />
        </Routes>
      </main>
    </div>
  );
}
