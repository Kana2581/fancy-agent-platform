import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';

import Sidebar from './Sidebar';
import { useAppContext } from '../context/AppContext';

const Layout: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('chat-theme');
    return saved ? saved === 'dark' : false;
  });
  const { selectedSession, setSelectedSession } = useAppContext();

  const toggleTheme = () => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem('chat-theme', next ? 'dark' : 'light');
      window.dispatchEvent(new CustomEvent('themechange', { detail: { isDark: next } }));
      return next;
    });
  };

  return (
    <div
      className={`flex h-screen overflow-hidden ${isDark ? 'dark' : ''} bg-gray-50 dark:bg-zinc-950`}
    >
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        isDark={isDark}
        onToggleTheme={toggleTheme}
        selectedSession={selectedSession}
        onSelectSession={setSelectedSession}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
};
export default Layout;
