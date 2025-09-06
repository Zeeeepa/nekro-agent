"""
Database models for LSP workspace management
"""

from tortoise import fields
from tortoise.models import Model


class DBLSPWorkspace(Model):
    """LSP workspace database model"""
    
    id = fields.IntField(pk=True)
    workspace_id = fields.CharField(max_length=255, unique=True, description="Unique workspace identifier")
    name = fields.CharField(max_length=255, description="Human-readable workspace name")
    path = fields.TextField(description="Absolute path to workspace directory")
    language = fields.CharField(max_length=50, default="python", description="Primary programming language")
    status = fields.CharField(max_length=20, default="inactive", description="Workspace status: active, inactive, error")
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_analyzed = fields.DatetimeField(null=True, description="Last time workspace was analyzed")
    
    # Configuration
    config = fields.JSONField(default=dict, description="Workspace-specific LSP configuration")
    
    # Statistics
    file_count = fields.IntField(default=0, description="Number of files in workspace")
    error_count = fields.IntField(default=0, description="Number of diagnostic errors")
    warning_count = fields.IntField(default=0, description="Number of diagnostic warnings")
    
    class Meta:
        table = "lsp_workspaces"
        table_description = "LSP workspace information"


class DBLSPDiagnostic(Model):
    """LSP diagnostic information database model"""
    
    id = fields.IntField(pk=True)
    workspace = fields.ForeignKeyField("models.DBLSPWorkspace", related_name="diagnostics", on_delete=fields.CASCADE)
    
    # File information
    file_path = fields.TextField(description="Relative path to file within workspace")
    file_uri = fields.TextField(description="LSP URI for the file")
    
    # Diagnostic details
    severity = fields.CharField(max_length=20, description="Diagnostic severity: error, warning, info, hint")
    message = fields.TextField(description="Diagnostic message")
    source = fields.CharField(max_length=100, null=True, description="Source of diagnostic (e.g., pylsp, mypy)")
    code = fields.CharField(max_length=100, null=True, description="Diagnostic code")
    
    # Location information
    start_line = fields.IntField(description="Start line (0-based)")
    start_character = fields.IntField(description="Start character (0-based)")
    end_line = fields.IntField(description="End line (0-based)")
    end_character = fields.IntField(description="End character (0-based)")
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    resolved = fields.BooleanField(default=False, description="Whether diagnostic has been resolved")
    
    class Meta:
        table = "lsp_diagnostics"
        table_description = "LSP diagnostic information"
        indexes = [
            ("workspace", "file_path"),
            ("workspace", "severity"),
            ("resolved",),
        ]


class DBLSPSymbol(Model):
    """LSP symbol information database model"""
    
    id = fields.IntField(pk=True)
    workspace = fields.ForeignKeyField("models.DBLSPWorkspace", related_name="symbols", on_delete=fields.CASCADE)
    
    # Symbol information
    name = fields.CharField(max_length=255, description="Symbol name")
    kind = fields.CharField(max_length=50, description="Symbol kind (class, function, variable, etc.)")
    container_name = fields.CharField(max_length=255, null=True, description="Container symbol name")
    
    # Location information
    file_path = fields.TextField(description="Relative path to file within workspace")
    file_uri = fields.TextField(description="LSP URI for the file")
    start_line = fields.IntField(description="Start line (0-based)")
    start_character = fields.IntField(description="Start character (0-based)")
    end_line = fields.IntField(description="End line (0-based)")
    end_character = fields.IntField(description="End character (0-based)")
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "lsp_symbols"
        table_description = "LSP symbol information"
        indexes = [
            ("workspace", "name"),
            ("workspace", "kind"),
            ("workspace", "file_path"),
        ]


class DBLSPProject(Model):
    """LSP project configuration database model"""
    
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, description="Project name")
    description = fields.TextField(null=True, description="Project description")
    
    # Project settings
    root_path = fields.TextField(description="Root path of the project")
    languages = fields.JSONField(default=list, description="List of programming languages in project")
    
    # LSP configuration
    lsp_config = fields.JSONField(default=dict, description="Project-specific LSP configuration")
    ignore_patterns = fields.JSONField(default=list, description="File patterns to ignore")
    
    # Relationships
    workspaces = fields.ReverseRelation["DBLSPWorkspace"]
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_indexed = fields.DatetimeField(null=True, description="Last time project was indexed")
    
    # Statistics
    total_files = fields.IntField(default=0, description="Total number of files in project")
    total_lines = fields.IntField(default=0, description="Total lines of code")
    
    class Meta:
        table = "lsp_projects"
        table_description = "LSP project configuration and metadata"
