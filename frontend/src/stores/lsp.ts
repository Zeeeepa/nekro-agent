/**
 * LSP state management store using Zustand
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { lspApi } from '../services/api/lsp';
import type {
  WorkspaceInfo,
  LSPDiagnostic,
  LSPSymbol,
  LSPLocation,
  LSPServerStatus,
  GetDiagnosticsResponse,
  FindSymbolResponse,
  GetReferencesResponse,
  GetDefinitionResponse,
  AnalyzeWorkspaceResponse,
} from '../services/api/lsp';

export interface LSPState {
  // Workspaces
  workspaces: WorkspaceInfo[];
  currentWorkspace: WorkspaceInfo | null;
  workspacesLoading: boolean;
  workspacesError: string | null;

  // Diagnostics
  diagnostics: LSPDiagnostic[];
  diagnosticsSummary: Record<string, number>;
  diagnosticsLoading: boolean;
  diagnosticsError: string | null;

  // Symbols
  symbols: LSPSymbol[];
  symbolsLoading: boolean;
  symbolsError: string | null;

  // References
  references: LSPLocation[];
  referencesLoading: boolean;
  referencesError: string | null;

  // Definition
  definition: LSPLocation | null;
  definitionLoading: boolean;
  definitionError: string | null;

  // Server status
  servers: LSPServerStatus[];
  serversLoading: boolean;
  serversError: string | null;

  // Analysis
  analysisResult: AnalyzeWorkspaceResponse | null;
  analysisLoading: boolean;
  analysisError: string | null;

  // UI state
  selectedDiagnostic: LSPDiagnostic | null;
  selectedSymbol: LSPSymbol | null;
  diagnosticsFilter: {
    severity?: string[];
    file?: string;
    resolved?: boolean;
  };
  symbolsFilter: {
    kind?: string[];
  };

  // Actions
  loadWorkspaces: () => Promise<void>;
  setCurrentWorkspace: (workspace: WorkspaceInfo | null) => void;
  createWorkspace: (request: {
    workspace_id: string;
    name: string;
    path: string;
    language?: string;
  }) => Promise<boolean>;
  deleteWorkspace: (workspaceId: string) => Promise<boolean>;
  
  loadDiagnostics: (workspaceId: string, filters?: {
    severity_filter?: string[];
    file_filter?: string;
    resolved_filter?: boolean;
  }) => Promise<void>;
  setDiagnosticsFilter: (filter: Partial<LSPState['diagnosticsFilter']>) => void;
  setSelectedDiagnostic: (diagnostic: LSPDiagnostic | null) => void;

  findSymbols: (workspaceId: string, symbolName: string, kindFilter?: string[]) => Promise<void>;
  setSymbolsFilter: (filter: Partial<LSPState['symbolsFilter']>) => void;
  setSelectedSymbol: (symbol: LSPSymbol | null) => void;

  getReferences: (workspaceId: string, filePath: string, line: number, character: number) => Promise<void>;
  getDefinition: (workspaceId: string, filePath: string, line: number, character: number) => Promise<void>;

  analyzeWorkspace: (workspaceId: string, forceRefresh?: boolean) => Promise<void>;

  loadServerStatus: () => Promise<void>;
  restartServer: (workspaceId: string, language?: string) => Promise<boolean>;

  // Utility actions
  clearErrors: () => void;
  reset: () => void;
}

const initialState = {
  // Workspaces
  workspaces: [],
  currentWorkspace: null,
  workspacesLoading: false,
  workspacesError: null,

  // Diagnostics
  diagnostics: [],
  diagnosticsSummary: {},
  diagnosticsLoading: false,
  diagnosticsError: null,

  // Symbols
  symbols: [],
  symbolsLoading: false,
  symbolsError: null,

  // References
  references: [],
  referencesLoading: false,
  referencesError: null,

  // Definition
  definition: null,
  definitionLoading: false,
  definitionError: null,

  // Server status
  servers: [],
  serversLoading: false,
  serversError: null,

  // Analysis
  analysisResult: null,
  analysisLoading: false,
  analysisError: null,

  // UI state
  selectedDiagnostic: null,
  selectedSymbol: null,
  diagnosticsFilter: {},
  symbolsFilter: {},
};

export const useLSPStore = create<LSPState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Workspace actions
      loadWorkspaces: async () => {
        set({ workspacesLoading: true, workspacesError: null });
        try {
          const response = await lspApi.getWorkspaces(0, 100);
          set({
            workspaces: response.workspaces,
            workspacesLoading: false,
          });
        } catch (error) {
          set({
            workspacesError: error instanceof Error ? error.message : 'Failed to load workspaces',
            workspacesLoading: false,
          });
        }
      },

      setCurrentWorkspace: (workspace) => {
        set({ currentWorkspace: workspace });
        // Clear related data when switching workspaces
        set({
          diagnostics: [],
          diagnosticsSummary: {},
          symbols: [],
          references: [],
          definition: null,
          analysisResult: null,
          selectedDiagnostic: null,
          selectedSymbol: null,
        });
      },

      createWorkspace: async (request) => {
        try {
          const response = await lspApi.createWorkspace(request);
          if (response.success) {
            // Reload workspaces
            await get().loadWorkspaces();
            return true;
          }
          return false;
        } catch (error) {
          set({
            workspacesError: error instanceof Error ? error.message : 'Failed to create workspace',
          });
          return false;
        }
      },

      deleteWorkspace: async (workspaceId) => {
        try {
          const response = await lspApi.deleteWorkspace(workspaceId);
          if (response.success) {
            // Remove from local state
            const workspaces = get().workspaces.filter(w => w.workspace_id !== workspaceId);
            set({ workspaces });
            
            // Clear current workspace if it was deleted
            const currentWorkspace = get().currentWorkspace;
            if (currentWorkspace?.workspace_id === workspaceId) {
              set({ currentWorkspace: null });
            }
            
            return true;
          }
          return false;
        } catch (error) {
          set({
            workspacesError: error instanceof Error ? error.message : 'Failed to delete workspace',
          });
          return false;
        }
      },

      // Diagnostics actions
      loadDiagnostics: async (workspaceId, filters = {}) => {
        set({ diagnosticsLoading: true, diagnosticsError: null });
        try {
          const response = await lspApi.getDiagnostics(workspaceId, filters);
          set({
            diagnostics: response.diagnostics,
            diagnosticsSummary: response.summary,
            diagnosticsLoading: false,
          });
        } catch (error) {
          set({
            diagnosticsError: error instanceof Error ? error.message : 'Failed to load diagnostics',
            diagnosticsLoading: false,
          });
        }
      },

      setDiagnosticsFilter: (filter) => {
        set((state) => ({
          diagnosticsFilter: { ...state.diagnosticsFilter, ...filter },
        }));
      },

      setSelectedDiagnostic: (diagnostic) => {
        set({ selectedDiagnostic: diagnostic });
      },

      // Symbols actions
      findSymbols: async (workspaceId, symbolName, kindFilter) => {
        set({ symbolsLoading: true, symbolsError: null });
        try {
          const response = await lspApi.findSymbols(workspaceId, {
            symbol_name: symbolName,
            kind_filter: kindFilter,
          });
          set({
            symbols: response.symbols,
            symbolsLoading: false,
          });
        } catch (error) {
          set({
            symbolsError: error instanceof Error ? error.message : 'Failed to find symbols',
            symbolsLoading: false,
          });
        }
      },

      setSymbolsFilter: (filter) => {
        set((state) => ({
          symbolsFilter: { ...state.symbolsFilter, ...filter },
        }));
      },

      setSelectedSymbol: (symbol) => {
        set({ selectedSymbol: symbol });
      },

      // References actions
      getReferences: async (workspaceId, filePath, line, character) => {
        set({ referencesLoading: true, referencesError: null });
        try {
          const response = await lspApi.getReferences(workspaceId, {
            file_path: filePath,
            line,
            character,
            include_declaration: true,
          });
          set({
            references: response.references,
            referencesLoading: false,
          });
        } catch (error) {
          set({
            referencesError: error instanceof Error ? error.message : 'Failed to get references',
            referencesLoading: false,
          });
        }
      },

      // Definition actions
      getDefinition: async (workspaceId, filePath, line, character) => {
        set({ definitionLoading: true, definitionError: null });
        try {
          const response = await lspApi.getDefinition(workspaceId, {
            file_path: filePath,
            line,
            character,
          });
          set({
            definition: response.definition || null,
            definitionLoading: false,
          });
        } catch (error) {
          set({
            definitionError: error instanceof Error ? error.message : 'Failed to get definition',
            definitionLoading: false,
          });
        }
      },

      // Analysis actions
      analyzeWorkspace: async (workspaceId, forceRefresh = false) => {
        set({ analysisLoading: true, analysisError: null });
        try {
          const response = await lspApi.analyzeWorkspace(workspaceId, {
            force_refresh: forceRefresh,
          });
          set({
            analysisResult: response,
            analysisLoading: false,
          });
          
          // Reload diagnostics after analysis
          if (response.success) {
            await get().loadDiagnostics(workspaceId);
          }
        } catch (error) {
          set({
            analysisError: error instanceof Error ? error.message : 'Failed to analyze workspace',
            analysisLoading: false,
          });
        }
      },

      // Server status actions
      loadServerStatus: async () => {
        set({ serversLoading: true, serversError: null });
        try {
          const response = await lspApi.getServerStatus();
          set({
            servers: response.servers,
            serversLoading: false,
          });
        } catch (error) {
          set({
            serversError: error instanceof Error ? error.message : 'Failed to load server status',
            serversLoading: false,
          });
        }
      },

      restartServer: async (workspaceId, language) => {
        try {
          const response = await lspApi.restartServer({ workspace_id: workspaceId, language });
          if (response.success) {
            // Reload server status
            await get().loadServerStatus();
            return true;
          }
          return false;
        } catch (error) {
          set({
            serversError: error instanceof Error ? error.message : 'Failed to restart server',
          });
          return false;
        }
      },

      // Utility actions
      clearErrors: () => {
        set({
          workspacesError: null,
          diagnosticsError: null,
          symbolsError: null,
          referencesError: null,
          definitionError: null,
          serversError: null,
          analysisError: null,
        });
      },

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'lsp-store',
    }
  )
);

export default useLSPStore;
