import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import Layout from './components/Layout';
import ChatPage from './pages/ChatPage';
import AgentsPage from './pages/AgentsPage';
import SettingsPage from './pages/SettingsPage';
import LLMSettingsPage from './pages/LLMSettingsPage';
import MCPSettingsPage from './pages/MCPSettingsPage';
import MCPDetailPage from './pages/MCPDetailPage';
import AuthPage from './pages/AuthPage';
import ScheduledTasksPage from './pages/ScheduledTasksPage';
import ApiToolsPage from './pages/ApiToolsPage';
import ImageToolsPage from './pages/ImageToolsPage';
import ImageStudioPage from './pages/ImageStudioPage';
import ImageGalleryPage from './pages/ImageGalleryPage';
import StatsPage from './pages/StatsPage';
import PromptTemplatesPage from './pages/PromptTemplatesPage';
import SkillsPage from './pages/SkillsPage';
import MemoryPage from './pages/MemoryPage';
import HelpPage from './pages/HelpPage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import AgentWebhooksPage from './pages/AgentWebhooksPage';
import PreferencesPage from './pages/PreferencesPage';
import SharedSessionPage from './pages/SharedSessionPage';
import { tokenManager } from './utils/TokenManager';

const ProtectedRoutes = () => {
  if (!tokenManager.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

const AuthRoutes = () => {
  if (tokenManager.isAuthenticated()) {
    return <Navigate to="/chat" replace />;
  }

  return <Outlet />;
};

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AuthRoutes />}>
            <Route path="/login" element={<AuthPage />} />
            <Route path="/register" element={<AuthPage />} />
          </Route>

          <Route path="/share/:slug" element={<SharedSessionPage />} />

          <Route element={<ProtectedRoutes />}>
            <Route path="/" element={<Layout />}>
              <Route path="chat" element={<ChatPage />} />
              <Route path="chat/:id" element={<ChatPage />} />
              <Route path="agents" element={<AgentsPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="llm-settings" element={<LLMSettingsPage />} />
              <Route path="mcp-settings" element={<MCPSettingsPage />} />
              <Route path="mcp/:id" element={<MCPDetailPage />} />
              <Route path="scheduled-tasks" element={<ScheduledTasksPage />} />
              <Route path="api-tools" element={<ApiToolsPage />} />
              <Route path="image-tools" element={<ImageToolsPage />} />
              <Route path="image-studio" element={<ImageStudioPage />} />
              <Route path="image-gallery" element={<ImageGalleryPage />} />
              <Route path="stats" element={<StatsPage />} />
              <Route path="prompt-templates" element={<PromptTemplatesPage />} />
              <Route path="skills" element={<SkillsPage />} />
              <Route path="memory" element={<MemoryPage />} />
              <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
              <Route path="webhooks" element={<AgentWebhooksPage />} />
              <Route path="preferences" element={<PreferencesPage />} />
              <Route path="help" element={<HelpPage />} />
              <Route index element={<Navigate to="/chat" replace />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
