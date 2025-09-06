"""
FastAPI routes for LSP functionality
"""

import asyncio
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse

from nekro_agent.core.logger import logger
from nekro_agent.models.db_lsp_workspace import DBLSPWorkspace, DBLSPDiagnostic, DBLSPSymbol, DBLSPProject
from nekro_agent.schemas.lsp import (
    CreateWorkspaceRequest,
    CreateWorkspaceResponse,
    WorkspaceInfo,
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
    LSPError,
    LSPErrorResponse,
    LSPDiagnostic,
    LSPSymbol,
    LSPLocation,
    LSPRange,
    LSPPosition,
    LSPServerStatus,
)
from nekro_agent.services.lsp_service import lsp_service
from nekro_agent.core.auth import get_current_user
from nekro_agent.models.db_user import DBUser

router = APIRouter(prefix="/lsp", tags=["LSP"])


@router.on_event("startup")
async def startup_lsp_service():
    """Initialize LSP service on startup"""
    try:
        await lsp_service.initialize()
        logger.info("LSP service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LSP service: {e}")


@router.on_event("shutdown")
async def shutdown_lsp_service():
    """Cleanup LSP service on shutdown"""
    try:
        await lsp_service.cleanup()
        logger.info("LSP service cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during LSP service cleanup: {e}")


@router.post("/workspaces", response_model=CreateWorkspaceResponse)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: DBUser = Depends(get_current_user)
) -> CreateWorkspaceResponse:
    """Create a new LSP workspace"""
    try:
        # Check if workspace already exists
        existing = await DBLSPWorkspace.filter(workspace_id=request.workspace_id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Workspace with ID '{request.workspace_id}' already exists"
            )
        
        # Create workspace in LSP service
        success = await lsp_service.create_workspace(
            workspace_id=request.workspace_id,
            workspace_path=request.path,
            language=request.language
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create workspace in LSP service"
            )
        
        # Create database record
        workspace = await DBLSPWorkspace.create(
            workspace_id=request.workspace_id,
            name=request.name,
            path=request.path,
            language=request.language,
            status="active"
        )
        
        logger.info(f"Created LSP workspace: {request.workspace_id}")
        
        return CreateWorkspaceResponse(
            success=True,
            workspace_id=request.workspace_id,
            message="Workspace created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces", response_model=GetWorkspacesResponse)
async def get_workspaces(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: DBUser = Depends(get_current_user)
) -> GetWorkspacesResponse:
    """Get all LSP workspaces"""
    try:
        # Get workspaces from database
        workspaces = await DBLSPWorkspace.all().offset(skip).limit(limit)
        total = await DBLSPWorkspace.all().count()
        
        workspace_infos = []
        for workspace in workspaces:
            workspace_infos.append(WorkspaceInfo(
                id=workspace.id,
                workspace_id=workspace.workspace_id,
                name=workspace.name,
                path=workspace.path,
                language=workspace.language,
                status=workspace.status,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                last_analyzed=workspace.last_analyzed,
                file_count=workspace.file_count,
                error_count=workspace.error_count,
                warning_count=workspace.warning_count,
                config=workspace.config
            ))
        
        return GetWorkspacesResponse(
            workspaces=workspace_infos,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error getting workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceInfo)
async def get_workspace(
    workspace_id: str,
    current_user: DBUser = Depends(get_current_user)
) -> WorkspaceInfo:
    """Get a specific LSP workspace"""
    try:
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return WorkspaceInfo(
            id=workspace.id,
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            path=workspace.path,
            language=workspace.language,
            status=workspace.status,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_analyzed=workspace.last_analyzed,
            file_count=workspace.file_count,
            error_count=workspace.error_count,
            warning_count=workspace.warning_count,
            config=workspace.config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: DBUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete an LSP workspace"""
    try:
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Delete from database (cascades to diagnostics and symbols)
        await workspace.delete()
        
        logger.info(f"Deleted LSP workspace: {workspace_id}")
        
        return {"success": True, "message": "Workspace deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/diagnostics", response_model=GetDiagnosticsResponse)
async def get_diagnostics(
    workspace_id: str,
    request: GetDiagnosticsRequest,
    current_user: DBUser = Depends(get_current_user)
) -> GetDiagnosticsResponse:
    """Get diagnostics for a workspace"""
    try:
        # Verify workspace exists
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Get diagnostics from LSP service
        lsp_diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
        
        # Convert to response format
        diagnostics = []
        severity_counts = {"error": 0, "warning": 0, "info": 0, "hint": 0}
        
        for diag in lsp_diagnostics:
            # Apply filters
            if request.severity_filter and diag["severity"] not in request.severity_filter:
                continue
            if request.file_filter and request.file_filter not in diag["file"]:
                continue
            
            diagnostics.append(LSPDiagnostic(
                file=diag["file"],
                severity=diag["severity"],
                message=diag["message"],
                range=LSPRange(
                    start=LSPPosition(
                        line=diag["range"]["start"]["line"],
                        character=diag["range"]["start"]["character"]
                    ),
                    end=LSPPosition(
                        line=diag["range"]["end"]["line"],
                        character=diag["range"]["end"]["character"]
                    )
                ),
                source=diag.get("source"),
                code=diag.get("code")
            ))
            
            # Count by severity
            severity = diag["severity"]
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        return GetDiagnosticsResponse(
            diagnostics=diagnostics,
            total=len(diagnostics),
            summary=severity_counts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diagnostics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/symbols/search", response_model=FindSymbolResponse)
async def find_symbols(
    workspace_id: str,
    request: FindSymbolRequest,
    current_user: DBUser = Depends(get_current_user)
) -> FindSymbolResponse:
    """Find symbols in a workspace"""
    try:
        # Verify workspace exists
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Find symbols using LSP service
        lsp_symbols = await lsp_service.find_symbol(workspace_id, request.symbol_name)
        
        # Convert to response format
        symbols = []
        for sym in lsp_symbols:
            # Apply kind filter
            if request.kind_filter and sym["kind"] not in request.kind_filter:
                continue
            
            symbols.append(LSPSymbol(
                name=sym["name"],
                kind=sym["kind"],
                location=LSPLocation(
                    uri=sym["location"]["uri"],
                    path=sym["location"]["path"],
                    range=LSPRange(
                        start=LSPPosition(
                            line=sym["location"]["range"]["start"]["line"],
                            character=sym["location"]["range"]["start"]["character"]
                        ),
                        end=LSPPosition(
                            line=sym["location"]["range"]["end"]["line"],
                            character=sym["location"]["range"]["end"]["character"]
                        )
                    )
                ),
                container_name=sym.get("container_name")
            ))
        
        return FindSymbolResponse(
            symbols=symbols,
            total=len(symbols)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/references", response_model=GetReferencesResponse)
async def get_references(
    workspace_id: str,
    request: GetReferencesRequest,
    current_user: DBUser = Depends(get_current_user)
) -> GetReferencesResponse:
    """Get references to a symbol"""
    try:
        # Verify workspace exists
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Get references using LSP service
        lsp_references = await lsp_service.get_symbol_references(
            workspace_id=workspace_id,
            file_path=request.file_path,
            line=request.line,
            character=request.character
        )
        
        # Convert to response format
        references = []
        for ref in lsp_references:
            references.append(LSPLocation(
                uri=ref["uri"],
                path=ref["path"],
                range=LSPRange(
                    start=LSPPosition(
                        line=ref["range"]["start"]["line"],
                        character=ref["range"]["start"]["character"]
                    ),
                    end=LSPPosition(
                        line=ref["range"]["end"]["line"],
                        character=ref["range"]["end"]["character"]
                    )
                )
            ))
        
        return GetReferencesResponse(
            references=references,
            total=len(references)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting references: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/definition", response_model=GetDefinitionResponse)
async def get_definition(
    workspace_id: str,
    request: GetDefinitionRequest,
    current_user: DBUser = Depends(get_current_user)
) -> GetDefinitionResponse:
    """Get definition of a symbol"""
    try:
        # Verify workspace exists
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Get definition using LSP service
        lsp_definition = await lsp_service.get_symbol_definition(
            workspace_id=workspace_id,
            file_path=request.file_path,
            line=request.line,
            character=request.character
        )
        
        definition = None
        if lsp_definition:
            definition = LSPLocation(
                uri=lsp_definition["uri"],
                path=lsp_definition["path"],
                range=LSPRange(
                    start=LSPPosition(
                        line=lsp_definition["range"]["start"]["line"],
                        character=lsp_definition["range"]["start"]["character"]
                    ),
                    end=LSPPosition(
                        line=lsp_definition["range"]["end"]["line"],
                        character=lsp_definition["range"]["end"]["character"]
                    )
                )
            )
        
        return GetDefinitionResponse(
            definition=definition,
            found=definition is not None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/analyze", response_model=AnalyzeWorkspaceResponse)
async def analyze_workspace(
    workspace_id: str,
    request: AnalyzeWorkspaceRequest,
    background_tasks: BackgroundTasks,
    current_user: DBUser = Depends(get_current_user)
) -> AnalyzeWorkspaceResponse:
    """Analyze a workspace for diagnostics and symbols"""
    try:
        # Verify workspace exists
        workspace = await DBLSPWorkspace.filter(workspace_id=workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        start_time = time.time()
        
        # Get diagnostics and symbols
        diagnostics = await lsp_service.get_workspace_diagnostics(workspace_id)
        
        # Update workspace statistics
        error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
        warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
        
        workspace.error_count = error_count
        workspace.warning_count = warning_count
        workspace.last_analyzed = asyncio.get_event_loop().time()
        await workspace.save()
        
        analysis_time = time.time() - start_time
        
        return AnalyzeWorkspaceResponse(
            success=True,
            diagnostics_count=len(diagnostics),
            symbols_count=0,  # TODO: Implement symbol counting
            files_analyzed=workspace.file_count,
            analysis_time=analysis_time,
            message="Workspace analyzed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/servers/status", response_model=GetServerStatusResponse)
async def get_server_status(
    current_user: DBUser = Depends(get_current_user)
) -> GetServerStatusResponse:
    """Get status of all LSP servers"""
    try:
        # TODO: Implement server status tracking in LSP service
        servers = []
        
        return GetServerStatusResponse(
            servers=servers,
            total_active=len(servers)
        )
        
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/restart", response_model=RestartServerResponse)
async def restart_server(
    request: RestartServerRequest,
    current_user: DBUser = Depends(get_current_user)
) -> RestartServerResponse:
    """Restart an LSP server"""
    try:
        # TODO: Implement server restart in LSP service
        
        return RestartServerResponse(
            success=True,
            message="Server restart initiated"
        )
        
    except Exception as e:
        logger.error(f"Error restarting server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers

@router.exception_handler(Exception)
async def lsp_exception_handler(request, exc):
    """Handle LSP-specific exceptions"""
    logger.error(f"LSP API error: {exc}")
    
    return LSPErrorResponse(
        error=LSPError(
            code="LSP_ERROR",
            message=str(exc),
            details={"request_path": str(request.url)}
        )
    )
