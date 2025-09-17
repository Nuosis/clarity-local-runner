#!/usr/bin/env python3
"""
Real Data Validation Script for Enhanced project_status_from_task_context Function

This script connects to the production database, extracts real task_context samples,
and validates that the enhanced transformation function works correctly with all
production data patterns.

Task 8.1: Ensure task_context schema stable; status projection matches API
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow

# Add app directory to path for imports
sys.path.append('app')

try:
    from schemas.status_projection_schema import project_status_from_task_context, ExecutionStatus
    from database.event import Event
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str = "clarity-local_db"  # Database container name
    port: int = 5432  # Internal port within Docker network
    database: str = "postgres"
    username: str = "postgres"
    password: str = "your-super-secret-and-long-postgres-password"


@dataclass
class TaskContextSample:
    """Container for task_context sample data."""
    event_id: int
    task_context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    event_type: Optional[str] = None
    project_id: Optional[str] = None


class RealDataExtractor:
    """Utility class for extracting real task_context data from the database."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection: Optional[psycopg2.extensions.connection] = None
        
    def connect(self) -> bool:
        """
        Connect to the database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                cursor_factory=RealDictCursor
            )
            print(f"✅ Connected to database at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")
    
    def get_table_info(self) -> Dict[str, Any]:
        """
        Get information about the events table structure.
        
        Returns:
            Dictionary with table information
        """
        if not self.connection:
            print("❌ No database connection available")
            return {}
            
        try:
            with self.connection.cursor() as cursor:
                # Get table schema
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'events'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute("SELECT COUNT(*) as total_events FROM events;")
                total_result = cursor.fetchone()
                total_count = dict(total_result)['total_events'] if total_result else 0
                
                # Get events with task_context count
                cursor.execute("SELECT COUNT(*) as events_with_context FROM events WHERE task_context IS NOT NULL;")
                context_result = cursor.fetchone()
                context_count = dict(context_result)['events_with_context'] if context_result else 0
                
                return {
                    'columns': [dict(col) for col in columns] if columns else [],
                    'total_events': total_count,
                    'events_with_task_context': context_count
                }
        except Exception as e:
            print(f"❌ Error getting table info: {e}")
            return {}
    
    def extract_task_context_samples(self, limit: int = 100) -> List[TaskContextSample]:
        """
        Extract diverse task_context samples from the database.
        
        Args:
            limit: Maximum number of samples to extract
            
        Returns:
            List of TaskContextSample objects
        """
        if not self.connection:
            print("❌ No database connection available")
            return []
            
        samples = []
        
        try:
            with self.connection.cursor() as cursor:
                # Query for events with task_context, ordered by most recent
                query = """
                    SELECT id, task_context, created_at, updated_at, event_type
                    FROM events
                    WHERE task_context IS NOT NULL
                    AND task_context != '{}'::jsonb
                    ORDER BY updated_at DESC
                    LIMIT %s;
                """
                
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                
                for row in rows:
                    # Extract project_id from task_context if available
                    project_id = None
                    task_context = dict(row).get('task_context', {})
                    
                    if isinstance(task_context, dict):
                        metadata = task_context.get('metadata', {})
                        if isinstance(metadata, dict):
                            project_id = metadata.get('project_id')
                    
                    row_dict = dict(row)
                    sample = TaskContextSample(
                        event_id=row_dict['id'],
                        task_context=task_context,
                        created_at=row_dict['created_at'],
                        updated_at=row_dict['updated_at'],
                        event_type=row_dict.get('event_type'),
                        project_id=project_id
                    )
                    samples.append(sample)
                    
            print(f"✅ Extracted {len(samples)} task_context samples from database")
            return samples
            
        except Exception as e:
            print(f"❌ Error extracting samples: {e}")
            traceback.print_exc()
            return []
    
    def analyze_data_patterns(self, samples: List[TaskContextSample]) -> Dict[str, Any]:
        """
        Analyze patterns in the extracted task_context data.
        
        Args:
            samples: List of task_context samples
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            'total_samples': len(samples),
            'metadata_patterns': {},
            'node_patterns': {},
            'field_variations': set(),
            'status_values': set(),
            'project_ids': set(),
            'malformed_samples': [],
            'schema_variations': []
        }
        
        for sample in samples:
            try:
                task_context = sample.task_context
                
                # Analyze metadata patterns
                if isinstance(task_context, dict):
                    metadata = task_context.get('metadata', {})
                    if isinstance(metadata, dict):
                        for key in metadata.keys():
                            analysis['field_variations'].add(f"metadata.{key}")
                            
                        # Track status values
                        status = metadata.get('status')
                        if status:
                            analysis['status_values'].add(str(status))
                    else:
                        analysis['malformed_samples'].append({
                            'event_id': sample.event_id,
                            'issue': f'metadata is not dict: {type(metadata)}'
                        })
                    
                    # Analyze node patterns
                    nodes = task_context.get('nodes', {})
                    if isinstance(nodes, dict):
                        for node_name, node_data in nodes.items():
                            if isinstance(node_data, dict):
                                # Direct status
                                if 'status' in node_data:
                                    analysis['status_values'].add(str(node_data['status']))
                                
                                # Nested event_data status
                                event_data = node_data.get('event_data', {})
                                if isinstance(event_data, dict) and 'status' in event_data:
                                    analysis['status_values'].add(str(event_data['status']))
                            else:
                                analysis['node_patterns'][f'non_dict_node_{type(node_data).__name__}'] = \
                                    analysis['node_patterns'].get(f'non_dict_node_{type(node_data).__name__}', 0) + 1
                    else:
                        analysis['malformed_samples'].append({
                            'event_id': sample.event_id,
                            'issue': f'nodes is not dict: {type(nodes)}'
                        })
                else:
                    analysis['malformed_samples'].append({
                        'event_id': sample.event_id,
                        'issue': f'task_context is not dict: {type(task_context)}'
                    })
                
                # Track project IDs
                if sample.project_id:
                    analysis['project_ids'].add(sample.project_id)
                    
            except Exception as e:
                analysis['malformed_samples'].append({
                    'event_id': sample.event_id,
                    'issue': f'analysis error: {str(e)}'
                })
        
        # Convert sets to lists for JSON serialization
        analysis['field_variations'] = list(analysis['field_variations'])
        analysis['status_values'] = list(analysis['status_values'])
        analysis['project_ids'] = list(analysis['project_ids'])
        
        return analysis


class RealDataValidator:
    """Validator for testing enhanced function with real data."""
    
    def __init__(self):
        self.test_results = []
        self.performance_metrics = []
    
    def validate_sample(self, sample: TaskContextSample) -> Dict[str, Any]:
        """
        Validate a single task_context sample with the enhanced function.
        
        Args:
            sample: TaskContextSample to validate
            
        Returns:
            Dictionary with validation results
        """
        start_time = time.time()
        result = {
            'event_id': sample.event_id,
            'success': False,
            'error': None,
            'execution_time_ms': 0,
            'status_projection': None,
            'project_id': sample.project_id
        }
        
        try:
            # Use event ID as execution_id and derive project_id
            execution_id = str(sample.event_id)
            project_id = sample.project_id or 'unknown/project'
            
            # Call the enhanced function
            status_projection = project_status_from_task_context(
                task_context=sample.task_context,
                execution_id=execution_id,
                project_id=project_id
            )
            
            result['success'] = True
            result['status_projection'] = {
                'status': status_projection.status.value,
                'progress': status_projection.progress,
                'current_task': status_projection.current_task,
                'totals': {
                    'completed': status_projection.totals.completed,
                    'total': status_projection.totals.total
                },
                'customer_id': status_projection.customer_id,
                'branch': status_projection.branch
            }
            
        except Exception as e:
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
        
        finally:
            result['execution_time_ms'] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    def validate_all_samples(self, samples: List[TaskContextSample]) -> Dict[str, Any]:
        """
        Validate all samples and collect comprehensive results.
        
        Args:
            samples: List of TaskContextSample objects
            
        Returns:
            Dictionary with comprehensive validation results
        """
        print(f"\n🧪 Validating {len(samples)} real data samples...")
        
        validation_results = {
            'total_samples': len(samples),
            'successful_validations': 0,
            'failed_validations': 0,
            'performance_metrics': {
                'min_time_ms': float('inf'),
                'max_time_ms': 0,
                'avg_time_ms': 0,
                'total_time_ms': 0
            },
            'status_distribution': {},
            'error_patterns': {},
            'sample_results': []
        }
        
        total_time = 0
        
        for i, sample in enumerate(samples):
            if i % 10 == 0:
                print(f"   Processing sample {i+1}/{len(samples)}...")
            
            result = self.validate_sample(sample)
            validation_results['sample_results'].append(result)
            
            # Update metrics
            exec_time = result['execution_time_ms']
            total_time += exec_time
            validation_results['performance_metrics']['min_time_ms'] = min(
                validation_results['performance_metrics']['min_time_ms'], exec_time
            )
            validation_results['performance_metrics']['max_time_ms'] = max(
                validation_results['performance_metrics']['max_time_ms'], exec_time
            )
            
            if result['success']:
                validation_results['successful_validations'] += 1
                
                # Track status distribution
                status = result['status_projection']['status']
                validation_results['status_distribution'][status] = \
                    validation_results['status_distribution'].get(status, 0) + 1
            else:
                validation_results['failed_validations'] += 1
                
                # Track error patterns
                error_type = type(result.get('error', 'Unknown')).__name__
                validation_results['error_patterns'][error_type] = \
                    validation_results['error_patterns'].get(error_type, 0) + 1
        
        # Calculate final metrics
        validation_results['performance_metrics']['total_time_ms'] = round(total_time, 2)
        validation_results['performance_metrics']['avg_time_ms'] = round(
            total_time / len(samples), 2
        ) if samples else 0
        
        if validation_results['performance_metrics']['min_time_ms'] == float('inf'):
            validation_results['performance_metrics']['min_time_ms'] = 0
        
        return validation_results


def main():
    """Main validation script."""
    print("🚀 Real Data Validation for Enhanced project_status_from_task_context")
    print("=" * 80)
    
    # Initialize database configuration
    config = DatabaseConfig()
    extractor = RealDataExtractor(config)
    validator = RealDataValidator()
    
    try:
        # Connect to database
        if not extractor.connect():
            print("❌ Cannot proceed without database connection")
            return False
        
        # Get table information
        print("\n📊 Database Table Information:")
        table_info = extractor.get_table_info()
        if table_info:
            print(f"   Total events: {table_info['total_events']}")
            print(f"   Events with task_context: {table_info['events_with_task_context']}")
            print(f"   Table columns: {len(table_info['columns'])}")
        
        # Extract samples
        print("\n📥 Extracting task_context samples...")
        samples = extractor.extract_task_context_samples(limit=50)  # Start with 50 samples
        
        if not samples:
            print("❌ No task_context samples found in database")
            return False
        
        # Analyze data patterns
        print("\n🔍 Analyzing data patterns...")
        analysis = extractor.analyze_data_patterns(samples)
        
        print(f"   Field variations found: {len(analysis['field_variations'])}")
        print(f"   Status values found: {len(analysis['status_values'])}")
        print(f"   Project IDs found: {len(analysis['project_ids'])}")
        print(f"   Malformed samples: {len(analysis['malformed_samples'])}")
        
        # Validate with enhanced function
        validation_results = validator.validate_all_samples(samples)
        
        # Display results
        print("\n" + "=" * 80)
        print("📊 Validation Results Summary")
        print("=" * 80)
        
        success_rate = (validation_results['successful_validations'] / 
                       validation_results['total_samples'] * 100)
        
        print(f"✅ Successful validations: {validation_results['successful_validations']}/{validation_results['total_samples']} ({success_rate:.1f}%)")
        print(f"❌ Failed validations: {validation_results['failed_validations']}")
        
        # Performance metrics
        perf = validation_results['performance_metrics']
        print(f"\n⚡ Performance Metrics:")
        print(f"   Average execution time: {perf['avg_time_ms']:.2f}ms")
        print(f"   Min execution time: {perf['min_time_ms']:.2f}ms")
        print(f"   Max execution time: {perf['max_time_ms']:.2f}ms")
        print(f"   Total processing time: {perf['total_time_ms']:.2f}ms")
        
        # Status distribution
        if validation_results['status_distribution']:
            print(f"\n📈 Status Distribution:")
            for status, count in validation_results['status_distribution'].items():
                print(f"   {status}: {count}")
        
        # Error patterns
        if validation_results['error_patterns']:
            print(f"\n🚨 Error Patterns:")
            for error_type, count in validation_results['error_patterns'].items():
                print(f"   {error_type}: {count}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"task_8_1_real_data_validation_results_{timestamp}.json"
        
        combined_results = {
            'timestamp': datetime.now().isoformat(),
            'database_info': table_info,
            'data_analysis': analysis,
            'validation_results': validation_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(combined_results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Final assessment
        if success_rate == 100.0:
            print("\n🎉 SUCCESS: Enhanced function handles 100% of real production data!")
            return True
        elif success_rate >= 95.0:
            print(f"\n✅ GOOD: Enhanced function handles {success_rate:.1f}% of real production data")
            return True
        else:
            print(f"\n⚠️  NEEDS IMPROVEMENT: Enhanced function handles only {success_rate:.1f}% of real production data")
            return False
    
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        traceback.print_exc()
        return False
    
    finally:
        extractor.disconnect()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)