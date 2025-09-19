/**
 * LSP API client for NekroAgent frontend
 */

import { apiClient } from './axios';
import type { AxiosResponse } from 'axios';

// Types
export interface LSPPosition {
  line: number;
  character: number;
}

export interface LSPRange {
  start: LSPPosition;
  end: LSPPosition;
}

export interface LSPLocation {
  uri: string;
  path: string;
  range: LSPRange;
}

export interface LSPDiagnostic {
  file: string;
  severity: 'error' | 'warning' | 'info' | 'hint';
  message: string;
  range: LSPRange;
  source?: string;
  code?: string;
}

export interface LSPSymbol {
  name: string;
  kind: string;
  location: LSPLocation;
  container_name?: string;
}

export interface WorkspaceInfo {
  id: number;
  workspace_id: string;
  name: string;
  path: string;
  language: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_analyzed?: string;
  file_count: number;
  error_count: number;
  warning_count: number;
  config: Record<string, any>;
}

export interface LSPServerStatus {
  language: string;
  status: 'running' | 'stopped' | 'error';
  workspace_path: string;
  pid?: number;
  uptime?: number;
  last_error?: string;
}

// Request/Response types
export interface CreateWorkspaceRequest {
  workspace_id: string;
  name: string;
  path: string;
  language?: string;
}

export interface CreateWorkspaceResponse {
  success: boolean;
  workspace_id: string;
  message?: string;
}

export interface GetWorkspacesResponse {
  workspaces: WorkspaceInfo[];
  total: number;
}

export interface GetDiagnosticsRequest {
  workspace_id: string;
  severity_filter?: string[];
  file_filter?: string;
  resolved_filter?: boolean;
}

export interface GetDiagnosticsResponse {
  diagnostics: LSPDiagnostic[];
  total: number;
  summary: Record<string, number>;
}

export interface FindSymbolRequest {
  workspace_id: string;
  symbol_name: string;
  kind_filter?: string[];
}

export interface FindSymbolResponse {
  symbols: LSPSymbol[];
  total: number;
}

export interface GetReferencesRequest {
  workspace_id: string;
  file_path: string;
  line: number;
  character: number;
  include_declaration?: boolean;
}

export interface GetReferencesResponse {
  references: LSPLocation[];
  total: number;
}

export interface GetDefinitionRequest {
  workspace_id: string;
  file_path: string;
  line: number;
  character: number;
}

export interface GetDefinitionResponse {
  definition?: LSPLocation;
  found: boolean;
}

export interface AnalyzeWorkspaceRequest {
  workspace_id: string;
  force_refresh?: boolean;
}

export interface AnalyzeWorkspaceResponse {
  success: boolean;
  diagnostics_count: number;
  symbols_count: number;
  files_analyzed: number;
  analysis_time: number;
  message?: string;
}

export interface GetServerStatusResponse {
  servers: LSPServerStatus[];
  total_active: number;
}

export interface RestartServerRequest {
  workspace_id: string;
  language?: string;
}

export interface RestartServerResponse {
  success: boolean;
  message?: string;
}

/**
 * LSP API client class
 */
export class LSPApi {
  private readonly baseUrl = '/api/lsp';

  /**
   * Create a new LSP workspace
   */
  async createWorkspace(request: CreateWorkspaceRequest): Promise<CreateWorkspaceResponse> {
    const response: AxiosResponse<CreateWorkspaceResponse> = await apiClient.post(
      `${this.baseUrl}/workspaces`,
      request
    );
    return response.data;
  }

  /**
   * Get all LSP workspaces
   */
  async getWorkspaces(skip = 0, limit = 10): Promise<GetWorkspacesResponse> {
    const response: AxiosResponse<GetWorkspacesResponse> = await apiClient.get(
      `${this.baseUrl}/workspaces`,
      {
        params: { skip, limit }
      }
    );
    return response.data;
  }

  /**
   * Get a specific workspace
   */
  async getWorkspace(workspaceId: string): Promise<WorkspaceInfo> {
    const response: AxiosResponse<WorkspaceInfo> = await apiClient.get(
      `${this.baseUrl}/workspaces/${workspaceId}`
    );
    return response.data;
  }

  /**
   * Delete a workspace
   */
  async deleteWorkspace(workspaceId: string): Promise<{ success: boolean; message: string }> {
    const response: AxiosResponse<{ success: boolean; message: string }> = await apiClient.delete(
      `${this.baseUrl}/workspaces/${workspaceId}`
    );
    return response.data;
  }

  /**
   * Get diagnostics for a workspace
   */
  async getDiagnostics(workspaceId: string, request: Omit<GetDiagnosticsRequest, 'workspace_id'>): Promise<GetDiagnosticsResponse> {
    const response: AxiosResponse<GetDiagnosticsResponse> = await apiClient.post(
      `${this.baseUrl}/workspaces/${workspaceId}/diagnostics`,
      { workspace_id: workspaceId, ...request }
    );
    return response.data;
  }

  /**
   * Find symbols in a workspace
   */
  async findSymbols(workspaceId: string, request: Omit<FindSymbolRequest, 'workspace_id'>): Promise<FindSymbolResponse> {
    const response: AxiosResponse<FindSymbolResponse> = await apiClient.post(
      `${this.baseUrl}/workspaces/${workspaceId}/symbols/search`,
      { workspace_id: workspaceId, ...request }
    );
    return response.data;
  }

  /**
   * Get symbol references
   */
  async getReferences(workspaceId: string, request: Omit<GetReferencesRequest, 'workspace_id'>): Promise<GetReferencesResponse> {
    const response: AxiosResponse<GetReferencesResponse> = await apiClient.post(
      `${this.baseUrl}/workspaces/${workspaceId}/references`,
      { workspace_id: workspaceId, ...request }
    );
    return response.data;
  }

  /**
   * Get symbol definition
   */
  async getDefinition(workspaceId: string, request: Omit<GetDefinitionRequest, 'workspace_id'>): Promise<GetDefinitionResponse> {
    const response: AxiosResponse<GetDefinitionResponse> = await apiClient.post(
      `${this.baseUrl}/workspaces/${workspaceId}/definition`,
      { workspace_id: workspaceId, ...request }
    );
    return response.data;
  }

  /**
   * Analyze a workspace
   */
  async analyzeWorkspace(workspaceId: string, request: Omit<AnalyzeWorkspaceRequest, 'workspace_id'>): Promise<AnalyzeWorkspaceResponse> {
    const response: AxiosResponse<AnalyzeWorkspaceResponse> = await apiClient.post(
      `${this.baseUrl}/workspaces/${workspaceId}/analyze`,
      { workspace_id: workspaceId, ...request }
    );
    return response.data;
  }

  /**
   * Get LSP server status
   */
  async getServerStatus(): Promise<GetServerStatusResponse> {
    const response: AxiosResponse<GetServerStatusResponse> = await apiClient.get(
      `${this.baseUrl}/servers/status`
    );
    return response.data;
  }

  /**
   * Restart LSP server
   */
  async restartServer(request: RestartServerRequest): Promise<RestartServerResponse> {
    const response: AxiosResponse<RestartServerResponse> = await apiClient.post(
      `${this.baseUrl}/servers/restart`,
      request
    );
    return response.data;
  }
}

// Export singleton instance
export const lspApi = new LSPApi();

// Export types
export type {
  LSPPosition,
  LSPRange,
  LSPLocation,
  LSPDiagnostic,
  LSPSymbol,
  WorkspaceInfo,
  LSPServerStatus,
  CreateWorkspaceRequest,
  CreateWorkspaceResponse,
  GetWorkspacesResponse,
  GetDiagnosticsRequest,
  GetDiagnosticsResponse,
  FindSymbolRequest,
  FindSymbolResponse,
  GetReferencesRequest,
  GetReferencesResponse,
  GetDefinitionRequest,
  GetDefinitionResponse,
  AnalyzeWorkspaceRequest,
  AnalyzeWorkspaceResponse,
  GetServerStatusResponse,
  RestartServerRequest,
  RestartServerResponse,
};

export default lspApi;
