import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { LLMOut, MCPOut, AgentOut } from '../api';
import { LlmModelsService, McpService, AgentsService } from '../api';
import { tokenManager } from '../utils/TokenManager';

export interface Agent {
  id: number;
  user_id: number;
  avatar: string;
  description: string;
  model_id: number;
  system_prompt: string;
  chat_window_size: number;
}

interface AppContextType {
  agents: AgentOut[];
  setAgents: React.Dispatch<React.SetStateAction<AgentOut[]>>;
  llmModels: LLMOut[];
  setLLMModels: React.Dispatch<React.SetStateAction<LLMOut[]>>;
  mcpTools: MCPOut[];
  setMCPTools: React.Dispatch<React.SetStateAction<MCPOut[]>>;
  refreshSessionsTrigger: number;
  refreshSessions: () => void;
  refreshLLMs: () => Promise<void>;
  refreshMCPs: () => Promise<void>;
  refreshAgents: () => Promise<void>;
  refreshAll: () => Promise<void>;
  selectedAgent: number | null;
  setSelectedAgent: React.Dispatch<React.SetStateAction<number | null>>;
  selectedSession: string | null;
  setSelectedSession: React.Dispatch<React.SetStateAction<string | null>>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// eslint-disable-next-line react-refresh/only-export-components -- context hook colocated with its provider; dev-only Fast Refresh hint
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};

interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [agents, setAgents] = useState<AgentOut[]>([]);
  const [llmModels, setLLMModels] = useState<LLMOut[]>([]);
  const [mcpTools, setMCPTools] = useState<MCPOut[]>([]);
  const [refreshSessionsTrigger, setRefreshSessionsTrigger] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState<number | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  const refreshSessions = useCallback(() => {
    setRefreshSessionsTrigger((n) => n + 1);
  }, []);

  const refreshLLMs = useCallback(async () => {
    if (!tokenManager.isAuthenticated()) return;
    try {
      const llms = await LlmModelsService.listLlmsApiV1LlmGet();
      setLLMModels(llms);
    } catch (error) {
      console.error('加载 LLM 列表失败:', error);
    }
  }, []);

  const refreshMCPs = useCallback(async () => {
    if (!tokenManager.isAuthenticated()) return;
    try {
      const mcps = await McpService.listMcpsApiV1McpsGet(0);
      setMCPTools(mcps);
    } catch (error) {
      console.error('加载 MCP 列表失败:', error);
    }
  }, []);

  const refreshAgents = useCallback(async () => {
    if (!tokenManager.isAuthenticated()) return;
    try {
      const agentsData = await AgentsService.listAgentsApiV1AgentsGet();
      setAgents(agentsData);
    } catch (error) {
      console.error('加载 Agent 列表失败:', error);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshLLMs(), refreshMCPs(), refreshAgents()]);
  }, [refreshLLMs, refreshMCPs, refreshAgents]);

  useEffect(() => {
    if (!tokenManager.isAuthenticated()) {
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async data fetch on mount; setState runs after await, not synchronously
    refreshAll();
  }, [refreshAll]);

  return (
    <AppContext.Provider
      value={{
        agents,
        setAgents,
        llmModels,
        setLLMModels,
        mcpTools,
        setMCPTools,
        refreshSessionsTrigger,
        refreshSessions,
        refreshLLMs,
        refreshMCPs,
        refreshAgents,
        refreshAll,
        selectedAgent,
        setSelectedAgent,
        selectedSession,
        setSelectedSession,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};
