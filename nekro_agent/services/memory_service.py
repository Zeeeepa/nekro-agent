"""
Memory service for project-specific knowledge management
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import in_transaction

from nekro_agent.core.logger import logger
from nekro_agent.models.db_memory import (
    DBProjectMemory,
    DBMemoryTag,
    DBMemoryLink,
    DBMemorySearch
)


class MemoryService:
    """Service for managing project memories"""
    
    def __init__(self):
        self.logger = logger
    
    async def save_memory(
        self,
        project_id: str,
        memory_name: str,
        content: str,
        memory_type: str = "general",
        tags: List[str] = None,
        priority: int = 0,
        created_by: str = None
    ) -> str:
        """Save or update a project memory
        
        Args:
            project_id: Project identifier
            memory_name: Memory name/key
            content: Memory content in markdown format
            memory_type: Memory type (general, onboarding, task, etc.)
            tags: List of tags for categorization
            priority: Memory priority (higher = more important)
            created_by: Creator identifier
            
        Returns:
            Success message
        """
        try:
            tags = tags or []
            content_hash = self._calculate_content_hash(content)
            content_length = len(content)
            
            async with in_transaction():
                # Try to get existing memory
                try:
                    memory = await DBProjectMemory.get(
                        project_id=project_id,
                        memory_name=memory_name
                    )
                    
                    # Update existing memory
                    memory.content = content
                    memory.memory_type = memory_type
                    memory.tags = tags
                    memory.priority = priority
                    memory.content_length = content_length
                    memory.content_hash = content_hash
                    memory.updated_at = datetime.now()
                    
                    if created_by:
                        memory.created_by = created_by
                    
                    await memory.save()
                    action = "updated"
                    
                except DoesNotExist:
                    # Create new memory
                    memory = await DBProjectMemory.create(
                        project_id=project_id,
                        memory_name=memory_name,
                        content=content,
                        memory_type=memory_type,
                        tags=tags,
                        priority=priority,
                        content_length=content_length,
                        content_hash=content_hash,
                        created_by=created_by
                    )
                    action = "created"
                
                # Update search index
                await self._update_search_index(memory)
                
                # Update tag usage counts
                await self._update_tag_usage(project_id, tags)
            
            self.logger.info(f"Memory {action}: {project_id}/{memory_name}")
            return f"Memory '{memory_name}' {action} successfully"
            
        except Exception as e:
            self.logger.error(f"Error saving memory {project_id}/{memory_name}: {e}")
            raise
    
    async def load_memory(
        self,
        project_id: str,
        memory_name: str,
        update_access: bool = True
    ) -> str:
        """Load a project memory
        
        Args:
            project_id: Project identifier
            memory_name: Memory name/key
            update_access: Whether to update access tracking
            
        Returns:
            Memory content
            
        Raises:
            DoesNotExist: If memory not found
        """
        try:
            memory = await DBProjectMemory.get(
                project_id=project_id,
                memory_name=memory_name
            )
            
            if update_access:
                # Update access tracking
                memory.access_count += 1
                memory.last_accessed = datetime.now()
                await memory.save(update_fields=["access_count", "last_accessed"])
            
            self.logger.debug(f"Memory loaded: {project_id}/{memory_name}")
            return memory.content
            
        except DoesNotExist:
            self.logger.warning(f"Memory not found: {project_id}/{memory_name}")
            raise KeyError(f"Memory '{memory_name}' not found in project '{project_id}'")
    
    async def list_memories(
        self,
        project_id: str,
        memory_type: str = None,
        tags: List[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List project memories
        
        Args:
            project_id: Project identifier
            memory_type: Filter by memory type
            tags: Filter by tags (memories must have all specified tags)
            limit: Maximum number of results
            
        Returns:
            List of memory information
        """
        try:
            query = DBProjectMemory.filter(project_id=project_id)
            
            if memory_type:
                query = query.filter(memory_type=memory_type)
            
            if tags:
                # Filter memories that contain all specified tags
                for tag in tags:
                    query = query.filter(tags__contains=tag)
            
            memories = await query.order_by("-priority", "-updated_at").limit(limit)
            
            result = []
            for memory in memories:
                result.append({
                    "name": memory.memory_name,
                    "type": memory.memory_type,
                    "tags": memory.tags,
                    "priority": memory.priority,
                    "content_length": memory.content_length,
                    "created_at": memory.created_at.isoformat(),
                    "updated_at": memory.updated_at.isoformat(),
                    "access_count": memory.access_count,
                    "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
                    "created_by": memory.created_by
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing memories for {project_id}: {e}")
            raise
    
    async def delete_memory(
        self,
        project_id: str,
        memory_name: str
    ) -> str:
        """Delete a project memory
        
        Args:
            project_id: Project identifier
            memory_name: Memory name/key
            
        Returns:
            Success message
            
        Raises:
            DoesNotExist: If memory not found
        """
        try:
            async with in_transaction():
                memory = await DBProjectMemory.get(
                    project_id=project_id,
                    memory_name=memory_name
                )
                
                # Delete search index entries
                await DBMemorySearch.filter(memory=memory).delete()
                
                # Delete memory links
                await DBMemoryLink.filter(source_memory=memory).delete()
                await DBMemoryLink.filter(target_memory=memory).delete()
                
                # Delete the memory
                await memory.delete()
            
            self.logger.info(f"Memory deleted: {project_id}/{memory_name}")
            return f"Memory '{memory_name}' deleted successfully"
            
        except DoesNotExist:
            self.logger.warning(f"Memory not found for deletion: {project_id}/{memory_name}")
            raise KeyError(f"Memory '{memory_name}' not found in project '{project_id}'")
    
    async def search_memories(
        self,
        project_id: str,
        query: str,
        memory_type: str = None,
        tags: List[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search project memories by content
        
        Args:
            project_id: Project identifier
            query: Search query
            memory_type: Filter by memory type
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            List of matching memories with relevance scores
        """
        try:
            # Build base query
            base_query = DBProjectMemory.filter(project_id=project_id)
            
            if memory_type:
                base_query = base_query.filter(memory_type=memory_type)
            
            if tags:
                for tag in tags:
                    base_query = base_query.filter(tags__contains=tag)
            
            # Simple text search (can be enhanced with full-text search later)
            search_terms = query.lower().split()
            matching_memories = []
            
            async for memory in base_query:
                content_lower = memory.content.lower()
                name_lower = memory.memory_name.lower()
                
                # Calculate relevance score
                score = 0
                for term in search_terms:
                    # Name matches are weighted higher
                    if term in name_lower:
                        score += 10
                    
                    # Content matches
                    score += content_lower.count(term)
                
                if score > 0:
                    matching_memories.append((memory, score))
            
            # Sort by relevance score
            matching_memories.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            results = []
            for memory, score in matching_memories[:limit]:
                # Extract relevant snippets
                snippets = self._extract_snippets(memory.content, search_terms)
                
                results.append({
                    "name": memory.memory_name,
                    "type": memory.memory_type,
                    "tags": memory.tags,
                    "priority": memory.priority,
                    "relevance_score": score,
                    "snippets": snippets,
                    "content_length": memory.content_length,
                    "created_at": memory.created_at.isoformat(),
                    "updated_at": memory.updated_at.isoformat(),
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching memories for {project_id}: {e}")
            raise
    
    async def get_memory_stats(self, project_id: str) -> Dict[str, Any]:
        """Get memory statistics for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Memory statistics
        """
        try:
            memories = await DBProjectMemory.filter(project_id=project_id)
            
            if not memories:
                return {
                    "total_memories": 0,
                    "total_content_length": 0,
                    "memory_types": {},
                    "tags": {},
                    "most_accessed": [],
                    "recently_updated": []
                }
            
            # Calculate statistics
            total_memories = len(memories)
            total_content_length = sum(m.content_length for m in memories)
            
            # Memory types distribution
            memory_types = {}
            for memory in memories:
                memory_types[memory.memory_type] = memory_types.get(memory.memory_type, 0) + 1
            
            # Tags distribution
            tags = {}
            for memory in memories:
                for tag in memory.tags:
                    tags[tag] = tags.get(tag, 0) + 1
            
            # Most accessed memories
            most_accessed = sorted(memories, key=lambda m: m.access_count, reverse=True)[:5]
            most_accessed_list = [
                {
                    "name": m.memory_name,
                    "access_count": m.access_count,
                    "last_accessed": m.last_accessed.isoformat() if m.last_accessed else None
                }
                for m in most_accessed
            ]
            
            # Recently updated memories
            recently_updated = sorted(memories, key=lambda m: m.updated_at, reverse=True)[:5]
            recently_updated_list = [
                {
                    "name": m.memory_name,
                    "updated_at": m.updated_at.isoformat(),
                    "type": m.memory_type
                }
                for m in recently_updated
            ]
            
            return {
                "total_memories": total_memories,
                "total_content_length": total_content_length,
                "average_content_length": total_content_length // total_memories if total_memories > 0 else 0,
                "memory_types": memory_types,
                "tags": tags,
                "most_accessed": most_accessed_list,
                "recently_updated": recently_updated_list
            }
            
        except Exception as e:
            self.logger.error(f"Error getting memory stats for {project_id}: {e}")
            raise
    
    # Private helper methods
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def _update_search_index(self, memory: DBProjectMemory):
        """Update search index for a memory"""
        try:
            # Delete existing search entries
            await DBMemorySearch.filter(memory=memory).delete()
            
            # Extract keywords and create searchable content
            keywords = self._extract_keywords(memory.content)
            search_content = f"{memory.memory_name} {memory.content}".lower()
            
            # Create new search entry
            await DBMemorySearch.create(
                memory=memory,
                search_content=search_content,
                keywords=keywords
            )
            
        except Exception as e:
            self.logger.error(f"Error updating search index for memory {memory.id}: {e}")
    
    async def _update_tag_usage(self, project_id: str, tags: List[str]):
        """Update tag usage counts"""
        try:
            for tag_name in tags:
                tag, created = await DBMemoryTag.get_or_create(
                    project_id=project_id,
                    tag_name=tag_name,
                    defaults={"usage_count": 0}
                )
                
                if not created:
                    # Recalculate usage count
                    usage_count = await DBProjectMemory.filter(
                        project_id=project_id,
                        tags__contains=tag_name
                    ).count()
                    
                    tag.usage_count = usage_count
                    await tag.save(update_fields=["usage_count"])
                    
        except Exception as e:
            self.logger.error(f"Error updating tag usage for {project_id}: {e}")
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Return unique keywords, limited to top 20
        return list(set(keywords))[:20]
    
    def _extract_snippets(self, content: str, search_terms: List[str], max_snippets: int = 3) -> List[str]:
        """Extract relevant snippets from content"""
        lines = content.split('\n')
        snippets = []
        
        for line in lines:
            line_lower = line.lower()
            if any(term in line_lower for term in search_terms):
                # Clean up the line and add context
                snippet = line.strip()
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."
                
                snippets.append(snippet)
                
                if len(snippets) >= max_snippets:
                    break
        
        return snippets


# Global memory service instance
memory_service = MemoryService()
