"""
Pydantic schemas for LSP functionality
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class LSPPosition(BaseModel):
    """LSP position schema"""
    line: int = Field(..., description="Line number (0-based)")
    character: int = Field(..., description="Character position (0-based)")


class LSPRange(BaseModel):
    """LSP range schema"""
    start: LSPPosition = Field(..., description="Start position")
    end: LSPPosition = Field(..., description="End position")


class LSPLocation(BaseModel):
    """LSP location schema"""
    uri: str = Field(..., description="File URI")
    path: str = Field(..., description="Absolute file path")
    range: LSPRange = Field(..., description="Location range")


class LSPDiagnosticSeverity(BaseModel):
    """LSP diagnostic severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class LSPDiagnostic(BaseModel):
    """LSP diagnostic schema"""
    file: str = Field(..., description="File path")
    severity: str = Field(..., description="Diagnostic severity")
    message: str = Field(..., description="Diagnostic message")
    range: LSPRange = Field(..., description="Diagnostic range")
    source: Optional[str] = Field(None, description="Diagnostic source")
    code: Optional[str] = Field(None, description="Diagnostic code")


class LSPSymbolKind(BaseModel):
    """LSP symbol kinds"""
    FILE = "file"
    MODULE = "module"
    NAMESPACE = "namespace"
    PACKAGE = "package"
    CLASS = "class"
    METHOD = "method"
    PROPERTY = "property"
    FIELD = "field"
    CONSTRUCTOR = "constructor"
    ENUM = "enum"
    INTERFACE = "interface"
    FUNCTION = "function"
    VARIABLE = "variable"
    CONSTANT = "constant"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    KEY = "key"
    NULL = "null"
    ENUM_MEMBER = "enumMember"
    STRUCT = "struct"
    EVENT = "event"
    OPERATOR = "operator"
    TYPE_PARAMETER = "typeParameter"


class LSPSymbol(BaseModel):
    """LSP symbol schema"""
    name: str = Field(..., description="Symbol name")
    kind: str = Field(..., description="Symbol kind")
    location: LSPLocation = Field(..., description="Symbol location")
    container_name: Optional[str] = Field(None, description="Container symbol name")


# Request/Response Schemas

class CreateWorkspaceRequest(BaseModel):
    """Request to create a new LSP workspace"""
    workspace_id: str = Field(..., description="Unique workspace identifier")
    name: str = Field(..., description="Human-readable workspace name")
    path: str = Field(..., description="Workspace directory path")
    language: str = Field(default="python", description="Primary programming language")


class CreateWorkspaceResponse(BaseModel):
    """Response for workspace creation"""
    success: bool = Field(..., description="Whether workspace was created successfully")
    workspace_id: str = Field(..., description="Workspace identifier")
    message: Optional[str] = Field(None, description="Success or error message")


class WorkspaceInfo(BaseModel):
    """Workspace information schema"""
    id: int = Field(..., description="Database ID")
    workspace_id: str = Field(..., description="Unique workspace identifier")
    name: str = Field(..., description="Human-readable workspace name")
    path: str = Field(..., description="Workspace directory path")
    language: str = Field(..., description="Primary programming language")
    status: str = Field(..., description="Workspace status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_analyzed: Optional[datetime] = Field(None, description="Last analysis timestamp")
    file_count: int = Field(..., description="Number of files in workspace")
    error_count: int = Field(..., description="Number of diagnostic errors")
    warning_count: int = Field(..., description="Number of diagnostic warnings")
    config: Dict[str, Any] = Field(default_factory=dict, description="Workspace configuration")


class GetWorkspacesResponse(BaseModel):
    """Response for getting workspaces"""
    workspaces: List[WorkspaceInfo] = Field(..., description="List of workspaces")
    total: int = Field(..., description="Total number of workspaces")


class GetDiagnosticsRequest(BaseModel):
    """Request to get workspace diagnostics"""
    workspace_id: str = Field(..., description="Workspace identifier")
    severity_filter: Optional[List[str]] = Field(None, description="Filter by severity levels")
    file_filter: Optional[str] = Field(None, description="Filter by file path pattern")
    resolved_filter: Optional[bool] = Field(None, description="Filter by resolved status")


class GetDiagnosticsResponse(BaseModel):
    """Response for getting diagnostics"""
    diagnostics: List[LSPDiagnostic] = Field(..., description="List of diagnostics")
    total: int = Field(..., description="Total number of diagnostics")
    summary: Dict[str, int] = Field(..., description="Summary by severity")


class FindSymbolRequest(BaseModel):
    """Request to find symbols"""
    workspace_id: str = Field(..., description="Workspace identifier")
    symbol_name: str = Field(..., description="Symbol name to search for")
    kind_filter: Optional[List[str]] = Field(None, description="Filter by symbol kinds")


class FindSymbolResponse(BaseModel):
    """Response for finding symbols"""
    symbols: List[LSPSymbol] = Field(..., description="List of found symbols")
    total: int = Field(..., description="Total number of symbols found")


class GetReferencesRequest(BaseModel):
    """Request to get symbol references"""
    workspace_id: str = Field(..., description="Workspace identifier")
    file_path: str = Field(..., description="File path")
    line: int = Field(..., description="Line number (0-based)")
    character: int = Field(..., description="Character position (0-based)")
    include_declaration: bool = Field(default=True, description="Include symbol declaration")


class GetReferencesResponse(BaseModel):
    """Response for getting references"""
    references: List[LSPLocation] = Field(..., description="List of reference locations")
    total: int = Field(..., description="Total number of references")


class GetDefinitionRequest(BaseModel):
    """Request to get symbol definition"""
    workspace_id: str = Field(..., description="Workspace identifier")
    file_path: str = Field(..., description="File path")
    line: int = Field(..., description="Line number (0-based)")
    character: int = Field(..., description="Character position (0-based)")


class GetDefinitionResponse(BaseModel):
    """Response for getting definition"""
    definition: Optional[LSPLocation] = Field(None, description="Definition location")
    found: bool = Field(..., description="Whether definition was found")


class AnalyzeWorkspaceRequest(BaseModel):
    """Request to analyze workspace"""
    workspace_id: str = Field(..., description="Workspace identifier")
    force_refresh: bool = Field(default=False, description="Force refresh of analysis")


class AnalyzeWorkspaceResponse(BaseModel):
    """Response for workspace analysis"""
    success: bool = Field(..., description="Whether analysis was successful")
    diagnostics_count: int = Field(..., description="Number of diagnostics found")
    symbols_count: int = Field(..., description="Number of symbols found")
    files_analyzed: int = Field(..., description="Number of files analyzed")
    analysis_time: float = Field(..., description="Analysis time in seconds")
    message: Optional[str] = Field(None, description="Success or error message")


class LSPServerStatus(BaseModel):
    """LSP server status schema"""
    language: str = Field(..., description="Programming language")
    status: str = Field(..., description="Server status: running, stopped, error")
    workspace_path: str = Field(..., description="Workspace path")
    pid: Optional[int] = Field(None, description="Process ID")
    uptime: Optional[float] = Field(None, description="Uptime in seconds")
    last_error: Optional[str] = Field(None, description="Last error message")


class GetServerStatusResponse(BaseModel):
    """Response for getting server status"""
    servers: List[LSPServerStatus] = Field(..., description="List of server statuses")
    total_active: int = Field(..., description="Number of active servers")


class RestartServerRequest(BaseModel):
    """Request to restart LSP server"""
    workspace_id: str = Field(..., description="Workspace identifier")
    language: Optional[str] = Field(None, description="Language server to restart")


class RestartServerResponse(BaseModel):
    """Response for restarting server"""
    success: bool = Field(..., description="Whether restart was successful")
    message: Optional[str] = Field(None, description="Success or error message")


# Error Schemas

class LSPError(BaseModel):
    """LSP error schema"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class LSPErrorResponse(BaseModel):
    """LSP error response schema"""
    error: LSPError = Field(..., description="Error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Configuration Schemas

class LSPLanguageConfig(BaseModel):
    """LSP language configuration schema"""
    language: str = Field(..., description="Programming language")
    server_command: List[str] = Field(..., description="Language server command")
    file_extensions: List[str] = Field(..., description="Supported file extensions")
    initialization_options: Dict[str, Any] = Field(default_factory=dict, description="Server initialization options")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Language server settings")


class LSPWorkspaceConfig(BaseModel):
    """LSP workspace configuration schema"""
    workspace_id: str = Field(..., description="Workspace identifier")
    languages: List[LSPLanguageConfig] = Field(..., description="Language configurations")
    ignore_patterns: List[str] = Field(default_factory=list, description="File patterns to ignore")
    max_file_size: int = Field(default=1048576, description="Maximum file size to analyze (bytes)")
    enable_diagnostics: bool = Field(default=True, description="Enable diagnostic analysis")
    enable_symbols: bool = Field(default=True, description="Enable symbol indexing")


class UpdateWorkspaceConfigRequest(BaseModel):
    """Request to update workspace configuration"""
    workspace_id: str = Field(..., description="Workspace identifier")
    config: LSPWorkspaceConfig = Field(..., description="New workspace configuration")


class UpdateWorkspaceConfigResponse(BaseModel):
    """Response for updating workspace configuration"""
    success: bool = Field(..., description="Whether update was successful")
    message: Optional[str] = Field(None, description="Success or error message")
