"""
Deterministic Prompt Service Module for Clarity Local Runner

This module provides deterministic prompt generation capabilities that create
Aider-focused code change instructions by combining Jinja2 templates with task
context from workflow nodes and repository information from Phase 4.

Primary Responsibility: Generate consistent, deterministic prompts for Aider tool integration
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from core.structured_logging import get_structured_logger, LogStatus, log_performance
from core.exceptions import ValidationError, ExternalServiceError
from services.prompt_loader import PromptManager
from services.repository_cache_manager import get_repository_cache_manager


@dataclass
class PromptContext:
    """
    Context data structure for prompt generation.
    
    This dataclass encapsulates all the information needed to generate
    deterministic prompts for Aider code change instructions.
    """
    task_id: str
    project_id: str
    execution_id: str
    correlation_id: Optional[str] = None
    
    # Task context from workflow nodes
    task_description: Optional[str] = None
    task_type: Optional[str] = None
    task_priority: Optional[str] = None
    current_node: Optional[str] = None
    workflow_status: Optional[str] = None
    
    # Repository context from Phase 4
    repository_url: Optional[str] = None
    repository_path: Optional[str] = None
    repository_branch: Optional[str] = None
    files_to_modify: Optional[List[str]] = None
    
    # Additional context
    user_id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DeterministicPromptService:
    """
    Deterministic prompt generation service for Aider-focused code change instructions.
    
    This service provides deterministic prompt generation that creates consistent
    prompts from the same inputs, integrating with workflow nodes and repository
    context to produce Aider-compatible code change instructions.
    
    Key Features:
    - Deterministic generation (same inputs = same outputs)
    - Aider tool integration focus
    - Template-based prompt construction
    - Repository context integration
    - Performance monitoring (≤2s requirement)
    - Comprehensive input validation
    - Security-focused output sanitization
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize the deterministic prompt service.
        
        Args:
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.logger = get_structured_logger(__name__)
        self.correlation_id = correlation_id
        self.prompt_manager = PromptManager()
        self.repository_manager = get_repository_cache_manager(correlation_id)
        
        # Set persistent context for logging
        if correlation_id:
            self.logger.set_context(correlationId=correlation_id)
    
    @log_performance(get_structured_logger(__name__), "generate_prompt")
    def generate_prompt(
        self,
        prompt_context: PromptContext,
        template_name: str = "aider_code_change",
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a deterministic prompt for Aider code change instructions.
        
        This method creates consistent prompts by combining Jinja2 templates with
        task context from workflow nodes and repository information. The generation
        process is deterministic, ensuring the same inputs always produce the same output.
        
        Args:
            prompt_context: Context data for prompt generation
            template_name: Name of the Jinja2 template to use (default: "aider_code_change")
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            Dictionary containing prompt generation results:
            {
                'success': bool,
                'prompt': str,
                'template_name': str,
                'context_hash': str,
                'generation_timestamp': str,
                'performance_metrics': Dict[str, float],
                'validation_status': str,
                'repository_context': Optional[Dict[str, Any]]
            }
            
        Raises:
            ValidationError: If input validation fails
            ExternalServiceError: If template loading or repository access fails
        """
        start_time = time.time()
        
        try:
            # Validate input parameters
            self._validate_prompt_context(prompt_context)
            self._validate_template_name(template_name)
            
            self.logger.info(
                "Starting deterministic prompt generation",
                correlation_id=self.correlation_id,
                project_id=project_id or prompt_context.project_id,
                execution_id=execution_id or prompt_context.execution_id,
                status=LogStatus.STARTED,
                template_name=template_name,
                task_id=prompt_context.task_id
            )
            
            # Generate deterministic context hash for consistency validation
            context_hash = self._generate_context_hash(prompt_context)
            
            # Enrich context with repository information
            repository_context = self._get_repository_context(prompt_context)
            
            # Prepare template variables
            template_variables = self._prepare_template_variables(
                prompt_context, repository_context
            )
            
            # Generate prompt using template
            prompt_generation_start = time.time()
            try:
                generated_prompt = self.prompt_manager.get_prompt(
                    template_name, **template_variables
                )
            except Exception as e:
                raise ExternalServiceError(
                    f"Failed to generate prompt from template: {str(e)}",
                    service="prompt_manager"
                )
            
            prompt_generation_duration = (time.time() - prompt_generation_start) * 1000
            
            # Validate and sanitize generated prompt
            validation_result = self._validate_generated_prompt(generated_prompt)
            
            # Calculate performance metrics
            total_duration = (time.time() - start_time) * 1000
            performance_metrics = {
                'total_duration_ms': round(total_duration, 2),
                'template_generation_duration_ms': round(prompt_generation_duration, 2),
                'context_preparation_duration_ms': round(total_duration - prompt_generation_duration, 2),
                'prompt_length': len(generated_prompt),
                'template_variables_count': len(template_variables)
            }
            
            # Build successful result
            result = {
                'success': True,
                'prompt': generated_prompt,
                'template_name': template_name,
                'context_hash': context_hash,
                'generation_timestamp': datetime.utcnow().isoformat() + "Z",
                'performance_metrics': performance_metrics,
                'validation_status': validation_result['status'],
                'repository_context': repository_context
            }
            
            self.logger.info(
                "Deterministic prompt generation completed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id or prompt_context.project_id,
                execution_id=execution_id or prompt_context.execution_id,
                status=LogStatus.COMPLETED,
                template_name=template_name,
                task_id=prompt_context.task_id,
                context_hash=context_hash,
                prompt_length=len(generated_prompt),
                total_duration_ms=performance_metrics['total_duration_ms'],
                validation_status=validation_result['status']
            )
            
            return result
            
        except (ValidationError, ExternalServiceError):
            # Re-raise known exceptions with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Deterministic prompt generation failed due to validation/service error",
                correlation_id=self.correlation_id,
                project_id=project_id or getattr(prompt_context, 'project_id', None),
                execution_id=execution_id or getattr(prompt_context, 'execution_id', None),
                status=LogStatus.FAILED,
                template_name=template_name,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Deterministic prompt generation failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id or getattr(prompt_context, 'project_id', None),
                execution_id=execution_id or getattr(prompt_context, 'execution_id', None),
                status=LogStatus.FAILED,
                template_name=template_name,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise ExternalServiceError(
                f"Prompt generation failed: {str(e)}",
                service="deterministic_prompt_service"
            )
    
    def _validate_prompt_context(self, prompt_context: PromptContext) -> None:
        """
        Validate prompt context for required fields and security.
        
        Args:
            prompt_context: Context to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(prompt_context, PromptContext):
            raise ValidationError(
                "prompt_context must be a PromptContext instance",
                field_errors=[{"field": "prompt_context", "error": "Invalid type"}]
            )
        
        # Validate required fields
        required_fields = ['task_id', 'project_id', 'execution_id']
        missing_fields = []
        
        for field in required_fields:
            value = getattr(prompt_context, field, None)
            if not value or not str(value).strip():
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                field_errors=[
                    {"field": field, "error": "Required field is missing or empty"}
                    for field in missing_fields
                ]
            )
        
        # Validate field formats for security
        import re
        
        # Task ID validation
        if not re.match(r'^[a-zA-Z0-9_-]+$', prompt_context.task_id):
            raise ValidationError(
                "task_id contains invalid characters",
                field_errors=[{"field": "task_id", "error": "Must contain only alphanumeric characters, underscores, and hyphens"}]
            )
        
        # Project ID validation (similar to DevTeam schema)
        if not re.match(r'^[a-zA-Z0-9_/-]+$', prompt_context.project_id):
            raise ValidationError(
                "project_id contains invalid characters",
                field_errors=[{"field": "project_id", "error": "Must contain only alphanumeric characters, underscores, hyphens, and forward slashes"}]
            )
    
    def _validate_template_name(self, template_name: str) -> None:
        """
        Validate template name for security and format.
        
        Args:
            template_name: Template name to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not template_name or not template_name.strip():
            raise ValidationError(
                "template_name cannot be empty",
                field_errors=[{"field": "template_name", "error": "Required field is missing or empty"}]
            )
        
        # Security validation - prevent path traversal
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', template_name):
            raise ValidationError(
                "template_name contains invalid characters",
                field_errors=[{"field": "template_name", "error": "Must contain only alphanumeric characters, underscores, and hyphens"}]
            )
        
        if '..' in template_name or '/' in template_name or '\\' in template_name:
            raise ValidationError(
                "template_name contains path traversal characters",
                field_errors=[{"field": "template_name", "error": "Path traversal not allowed"}]
            )
    
    def _generate_context_hash(self, prompt_context: PromptContext) -> str:
        """
        Generate a deterministic hash of the prompt context for consistency validation.
        
        Args:
            prompt_context: Context to hash
            
        Returns:
            Hexadecimal hash string
        """
        import hashlib
        import json
        
        # Create a normalized representation of the context
        context_dict = {
            'task_id': prompt_context.task_id,
            'project_id': prompt_context.project_id,
            'execution_id': prompt_context.execution_id,
            'task_description': prompt_context.task_description or '',
            'task_type': prompt_context.task_type or '',
            'task_priority': prompt_context.task_priority or '',
            'current_node': prompt_context.current_node or '',
            'workflow_status': prompt_context.workflow_status or '',
            'repository_url': prompt_context.repository_url or '',
            'repository_branch': prompt_context.repository_branch or '',
            'files_to_modify': sorted(prompt_context.files_to_modify or []),
            'user_id': prompt_context.user_id or ''
        }
        
        # Create deterministic JSON representation
        context_json = json.dumps(context_dict, sort_keys=True, separators=(',', ':'))
        
        # Generate SHA-256 hash
        return hashlib.sha256(context_json.encode('utf-8')).hexdigest()[:16]
    
    def _get_repository_context(self, prompt_context: PromptContext) -> Optional[Dict[str, Any]]:
        """
        Get repository context information from Phase 4 integration.
        
        Args:
            prompt_context: Context containing repository information
            
        Returns:
            Repository context dictionary or None if not available
        """
        if not prompt_context.repository_url:
            return None
        
        try:
            # Get repository cache information
            cache_info = self.repository_manager.get_repository_cache_info(
                repository_url=prompt_context.repository_url,
                project_id=prompt_context.project_id,
                execution_id=prompt_context.execution_id
            )
            
            if cache_info:
                return {
                    'repository_url': prompt_context.repository_url,
                    'repository_path': cache_info.get('cache_path'),
                    'repository_branch': prompt_context.repository_branch or 'main',
                    'repository_size_bytes': cache_info.get('size_bytes', 0),
                    'file_count': cache_info.get('file_count', 0),
                    'last_updated': cache_info.get('last_modified'),
                    'is_valid': cache_info.get('is_valid', False)
                }
            
            return {
                'repository_url': prompt_context.repository_url,
                'repository_path': None,
                'repository_branch': prompt_context.repository_branch or 'main',
                'repository_size_bytes': 0,
                'file_count': 0,
                'last_updated': None,
                'is_valid': False
            }
            
        except Exception as e:
            self.logger.warn(
                "Failed to get repository context",
                correlation_id=self.correlation_id,
                project_id=prompt_context.project_id,
                execution_id=prompt_context.execution_id,
                repository_url=prompt_context.repository_url,
                error=str(e)
            )
            return None
    
    def _prepare_template_variables(
        self,
        prompt_context: PromptContext,
        repository_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Prepare variables for template rendering.
        
        Args:
            prompt_context: Context data for prompt generation
            repository_context: Repository context information
            
        Returns:
            Dictionary of template variables
        """
        # Base template variables
        template_vars = {
            'task_id': prompt_context.task_id,
            'project_id': prompt_context.project_id,
            'execution_id': prompt_context.execution_id,
            'correlation_id': prompt_context.correlation_id or f"corr_{prompt_context.execution_id}",
            'generation_timestamp': datetime.utcnow().isoformat() + "Z",
            
            # Task context
            'task_description': prompt_context.task_description or 'No description provided',
            'task_type': prompt_context.task_type or 'atomic',
            'task_priority': prompt_context.task_priority or 'medium',
            'current_node': prompt_context.current_node or 'unknown',
            'workflow_status': prompt_context.workflow_status or 'in_progress',
            
            # Files and modifications
            'files_to_modify': prompt_context.files_to_modify or [],
            'files_count': len(prompt_context.files_to_modify or []),
            
            # User context
            'user_id': prompt_context.user_id or 'system',
            
            # Additional metadata
            'metadata': prompt_context.metadata or {}
        }
        
        # Add repository context if available
        if repository_context:
            template_vars.update({
                'repository_url': repository_context.get('repository_url'),
                'repository_path': repository_context.get('repository_path'),
                'repository_branch': repository_context.get('repository_branch'),
                'repository_size_bytes': repository_context.get('repository_size_bytes', 0),
                'repository_file_count': repository_context.get('file_count', 0),
                'repository_last_updated': repository_context.get('last_updated'),
                'repository_is_valid': repository_context.get('is_valid', False)
            })
        else:
            template_vars.update({
                'repository_url': prompt_context.repository_url,
                'repository_path': None,
                'repository_branch': prompt_context.repository_branch or 'main',
                'repository_size_bytes': 0,
                'repository_file_count': 0,
                'repository_last_updated': None,
                'repository_is_valid': False
            })
        
        return template_vars
    
    def _validate_generated_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validate and sanitize the generated prompt.
        
        Args:
            prompt: Generated prompt to validate
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            'status': 'valid',
            'issues': [],
            'prompt_length': len(prompt),
            'line_count': len(prompt.split('\n'))
        }
        
        # Basic validation
        if not prompt or not prompt.strip():
            validation_result['status'] = 'invalid'
            validation_result['issues'].append('Generated prompt is empty')
            return validation_result
        
        # Length validation
        if len(prompt) < 50:
            validation_result['status'] = 'warning'
            validation_result['issues'].append('Generated prompt is very short')
        elif len(prompt) > 50000:
            validation_result['status'] = 'warning'
            validation_result['issues'].append('Generated prompt is very long')
        
        # Security validation - check for potentially dangerous content
        import re
        dangerous_patterns = [
            re.compile(r'<script', re.IGNORECASE),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')  # Control characters except \t, \n, \r
        ]
        
        for pattern in dangerous_patterns:
            if pattern.search(prompt):
                validation_result['status'] = 'invalid'
                validation_result['issues'].append('Generated prompt contains potentially dangerous content')
                break
        
        return validation_result


def get_deterministic_prompt_service(correlation_id: Optional[str] = None) -> DeterministicPromptService:
    """
    Factory function to get a deterministic prompt service instance.
    
    Args:
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        DeterministicPromptService instance
    """
    return DeterministicPromptService(correlation_id=correlation_id)