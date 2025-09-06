"""
Database models for project memory management
"""

from tortoise import fields
from tortoise.models import Model


class DBProjectMemory(Model):
    """Project memory database model"""
    
    id = fields.IntField(pk=True)
    project_id = fields.CharField(max_length=255, description="Project identifier")
    memory_name = fields.CharField(max_length=255, description="Memory name/key")
    content = fields.TextField(description="Memory content in markdown format")
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_by = fields.CharField(max_length=255, null=True, description="Creator identifier")
    
    # Memory properties
    memory_type = fields.CharField(
        max_length=50, 
        default="general",
        description="Memory type: general, onboarding, task, code_analysis, etc."
    )
    tags = fields.JSONField(default=list, description="Memory tags for categorization")
    priority = fields.IntField(default=0, description="Memory priority (higher = more important)")
    
    # Usage tracking
    access_count = fields.IntField(default=0, description="Number of times accessed")
    last_accessed = fields.DatetimeField(null=True, description="Last access timestamp")
    
    # Content metadata
    content_length = fields.IntField(default=0, description="Content length in characters")
    content_hash = fields.CharField(max_length=64, null=True, description="Content hash for change detection")
    
    class Meta:
        table = "project_memories"
        table_description = "Project-specific memory storage"
        unique_together = [("project_id", "memory_name")]
        indexes = [
            ("project_id", "memory_type"),
            ("project_id", "priority"),
            ("created_at",),
            ("last_accessed",),
        ]


class DBMemoryTag(Model):
    """Memory tag database model"""
    
    id = fields.IntField(pk=True)
    project_id = fields.CharField(max_length=255, description="Project identifier")
    tag_name = fields.CharField(max_length=100, description="Tag name")
    description = fields.TextField(null=True, description="Tag description")
    color = fields.CharField(max_length=7, null=True, description="Tag color (hex)")
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    usage_count = fields.IntField(default=0, description="Number of memories using this tag")
    
    class Meta:
        table = "memory_tags"
        table_description = "Memory tags for categorization"
        unique_together = [("project_id", "tag_name")]


class DBMemoryLink(Model):
    """Memory link database model for relationships between memories"""
    
    id = fields.IntField(pk=True)
    source_memory = fields.ForeignKeyField("models.DBProjectMemory", related_name="outgoing_links")
    target_memory = fields.ForeignKeyField("models.DBProjectMemory", related_name="incoming_links")
    
    link_type = fields.CharField(
        max_length=50,
        default="related",
        description="Link type: related, depends_on, supersedes, etc."
    )
    description = fields.TextField(null=True, description="Link description")
    
    # Metadata
    created_at = fields.DatetimeField(auto_now_add=True)
    created_by = fields.CharField(max_length=255, null=True, description="Creator identifier")
    
    class Meta:
        table = "memory_links"
        table_description = "Links between memories"
        unique_together = [("source_memory", "target_memory", "link_type")]


class DBMemorySearch(Model):
    """Memory search index for full-text search"""
    
    id = fields.IntField(pk=True)
    memory = fields.ForeignKeyField("models.DBProjectMemory", related_name="search_entries")
    
    # Search fields
    search_content = fields.TextField(description="Searchable content (processed)")
    keywords = fields.JSONField(default=list, description="Extracted keywords")
    
    # Search metadata
    language = fields.CharField(max_length=10, default="en", description="Content language")
    last_indexed = fields.DatetimeField(auto_now=True, description="Last indexing timestamp")
    
    class Meta:
        table = "memory_search"
        table_description = "Memory search index"
