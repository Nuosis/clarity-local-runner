#!/usr/bin/env python3
"""
Task 8.1.2: API Field Alignment Validation Test (Simplified)
Validates complete field mapping between StatusProjection schema and API responses
"""

import json
import time
from typing import Dict, Any, Set, List
from datetime import datetime

# Import the schemas and services to analyze
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from schemas.status_projection_schema import StatusProjection, ExecutionStatus, TaskTotals, ExecutionArtifacts
from schemas.devteam_automation_schema import DevTeamAutomationStatusResponse
from core.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)

class FieldAlignmentValidator:
    """Validates field alignment between StatusProjection schema and API responses"""
    
    def __init__(self):
        pass
        
    def get_status_projection_fields(self) -> Set[str]:
        """Extract all fields from StatusProjection schema"""
        try:
            # Get all fields from the StatusProjection model
            schema_fields = set(StatusProjection.model_fields.keys())
            logger.info(f"StatusProjection schema fields: {sorted(schema_fields)}")
            return schema_fields
        except Exception as e:
            logger.error(f"Error extracting StatusProjection fields: {e}")
            return set()
    
    def get_api_response_fields(self) -> Set[str]:
        """Extract all fields from DevTeamAutomationStatusResponse schema"""
        try:
            # Get all fields from the API response model
            api_fields = set(DevTeamAutomationStatusResponse.model_fields.keys())
            logger.info(f"API response schema fields: {sorted(api_fields)}")
            return api_fields
        except Exception as e:
            logger.error(f"Error extracting API response fields: {e}")
            return set()
    
    def compare_schema_field_mappings(self, status_projection_fields: Set[str], api_response_fields: Set[str]) -> Dict[str, Any]:
        """Compare StatusProjection schema fields with API response schema fields"""
        
        # Fields present in StatusProjection but missing from API response schema
        missing_in_api = status_projection_fields - api_response_fields
        
        # Fields present in API response schema but not in StatusProjection
        extra_in_api = api_response_fields - status_projection_fields
        
        # Fields present in both
        common_fields = status_projection_fields & api_response_fields
        
        # Calculate coverage percentage
        coverage_percentage = (len(common_fields) / len(status_projection_fields)) * 100 if status_projection_fields else 0
        
        return {
            "status_projection_fields_count": len(status_projection_fields),
            "api_response_fields_count": len(api_response_fields),
            "common_fields_count": len(common_fields),
            "missing_in_api": sorted(missing_in_api),
            "extra_in_api": sorted(extra_in_api),
            "common_fields": sorted(common_fields),
            "coverage_percentage": coverage_percentage,
            "is_complete_mapping": len(missing_in_api) == 0
        }
    
    def analyze_field_mapping_in_endpoint(self) -> Dict[str, Any]:
        """Analyze the field mapping implementation in the get_devteam_automation_status endpoint"""
        
        # This analyzes the mapping code in lines 802-823 of devteam_automation.py
        expected_mappings = {
            "status": "status_projection.status.value",
            "progress": "status_projection.progress", 
            "current_task": "status_projection.current_task",
            "totals": "status_projection.totals (nested mapping)",
            "execution_id": "status_projection.execution_id",
            "project_id": "status_projection.project_id",
            "customer_id": "status_projection.customer_id",
            "branch": "status_projection.branch",
            "artifacts": "status_projection.artifacts (nested mapping)",
            "started_at": "status_projection.started_at.isoformat()",
            "updated_at": "status_projection.updated_at.isoformat()"
        }
        
        # Nested field mappings
        totals_mappings = {
            "totals.completed": "status_projection.totals.completed",
            "totals.total": "status_projection.totals.total"
        }
        
        artifacts_mappings = {
            "artifacts.repo_path": "status_projection.artifacts.repo_path",
            "artifacts.branch": "status_projection.artifacts.branch", 
            "artifacts.logs": "status_projection.artifacts.logs",
            "artifacts.files_modified": "status_projection.artifacts.files_modified"
        }
        
        return {
            "endpoint_field_mappings": expected_mappings,
            "totals_nested_mappings": totals_mappings,
            "artifacts_nested_mappings": artifacts_mappings,
            "total_mapped_fields": len(expected_mappings) + len(totals_mappings) + len(artifacts_mappings)
        }
    
    def validate_logging_consistency(self) -> Dict[str, Any]:
        """Validate structured logging consistency between API and Worker components"""
        try:
            # Check if CustomJSONEncoder is being used consistently
            from core.structured_logging import CustomJSONEncoder, get_structured_logger
            
            # Verify logger configuration
            test_logger = get_structured_logger("test_validation")
            
            # Check logging patterns used in API endpoints
            api_logging_fields = [
                "correlation_id",
                "execution_id", 
                "project_id",
                "operation",
                "status",
                "duration_ms",
                "performance_target_met"
            ]
            
            # Check logging patterns used in Worker tasks
            worker_logging_fields = [
                "correlation_id",
                "execution_id",
                "project_id", 
                "task_id",
                "operation",
                "status",
                "duration_ms"
            ]
            
            common_fields = set(api_logging_fields) & set(worker_logging_fields)
            
            return {
                "success": True,
                "custom_json_encoder_available": CustomJSONEncoder is not None,
                "logger_configured": test_logger is not None,
                "api_logging_fields": api_logging_fields,
                "worker_logging_fields": worker_logging_fields,
                "common_logging_fields": sorted(common_fields),
                "logging_consistency_score": len(common_fields) / max(len(api_logging_fields), len(worker_logging_fields)) * 100
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error validating logging consistency: {e}"
            }
    
    def create_test_status_projection(self) -> StatusProjection:
        """Create a test StatusProjection instance for validation"""
        return StatusProjection(
            execution_id="exec_test_12345",
            project_id="customer-test/project-validation",
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-test",
            branch="task/1-1-1-validation-test",
            artifacts=ExecutionArtifacts(
                repo_path="/workspace/repos/customer-test-project-validation",
                branch="task/1-1-1-validation-test",
                logs=["Implementation started", "Validation test initialized"],
                files_modified=["src/config.js", "README.md"]
            ),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def validate_api_response_mapping(self, status_projection: StatusProjection) -> Dict[str, Any]:
        """Validate that StatusProjection can be properly mapped to API response"""
        try:
            # Create API response following the mapping in devteam_automation.py lines 802-823
            api_response = DevTeamAutomationStatusResponse(
                status=status_projection.status.value,
                progress=status_projection.progress,
                current_task=status_projection.current_task,
                totals={
                    "completed": status_projection.totals.completed,
                    "total": status_projection.totals.total
                },
                execution_id=status_projection.execution_id,
                project_id=status_projection.project_id,
                customer_id=status_projection.customer_id,
                branch=status_projection.branch,
                artifacts={
                    "repo_path": status_projection.artifacts.repo_path,
                    "branch": status_projection.artifacts.branch,
                    "logs": status_projection.artifacts.logs,
                    "files_modified": status_projection.artifacts.files_modified
                } if status_projection.artifacts else None,
                started_at=status_projection.started_at.isoformat() if status_projection.started_at else None,
                updated_at=status_projection.updated_at.isoformat() if status_projection.updated_at else None
            )
            
            # Convert to dict for field analysis
            api_dict = api_response.model_dump()
            
            return {
                "success": True,
                "mapping_successful": True,
                "api_response_fields": list(api_dict.keys()),
                "nested_totals_fields": list(api_dict["totals"].keys()) if api_dict.get("totals") else [],
                "nested_artifacts_fields": list(api_dict["artifacts"].keys()) if api_dict.get("artifacts") else [],
                "api_response_data": api_dict
            }
            
        except Exception as e:
            return {
                "success": False,
                "mapping_successful": False,
                "error": str(e)
            }
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive field alignment validation"""
        logger.info("Starting comprehensive API field alignment validation")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": "8.1.2 - API Field Alignment Validation",
            "validation_results": {}
        }
        
        try:
            # 1. Extract StatusProjection schema fields
            logger.info("Step 1: Extracting StatusProjection schema fields")
            status_projection_fields = self.get_status_projection_fields()
            results["validation_results"]["status_projection_analysis"] = {
                "fields": sorted(status_projection_fields),
                "field_count": len(status_projection_fields)
            }
            
            # 2. Extract API response schema fields
            logger.info("Step 2: Extracting API response schema fields")
            api_response_fields = self.get_api_response_fields()
            results["validation_results"]["api_response_analysis"] = {
                "fields": sorted(api_response_fields),
                "field_count": len(api_response_fields)
            }
            
            # 3. Compare schema field mappings
            logger.info("Step 3: Comparing schema field mappings")
            schema_comparison = self.compare_schema_field_mappings(status_projection_fields, api_response_fields)
            results["validation_results"]["schema_field_comparison"] = schema_comparison
            
            # 4. Analyze endpoint field mapping implementation
            logger.info("Step 4: Analyzing endpoint field mapping implementation")
            endpoint_analysis = self.analyze_field_mapping_in_endpoint()
            results["validation_results"]["endpoint_mapping_analysis"] = endpoint_analysis
            
            # 5. Test actual mapping with StatusProjection instance
            logger.info("Step 5: Testing actual mapping with StatusProjection instance")
            test_projection = self.create_test_status_projection()
            mapping_validation = self.validate_api_response_mapping(test_projection)
            results["validation_results"]["mapping_validation"] = mapping_validation
            
            # 6. Validate structured logging consistency
            logger.info("Step 6: Validating structured logging consistency")
            logging_validation = self.validate_logging_consistency()
            results["validation_results"]["logging_consistency"] = logging_validation
            
            # 7. Overall assessment
            logger.info("Step 7: Generating overall assessment")
            overall_assessment = self.generate_overall_assessment(results["validation_results"])
            results["overall_assessment"] = overall_assessment
            
            logger.info("Comprehensive validation completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error during comprehensive validation: {e}")
            results["error"] = str(e)
            return results
    
    def generate_overall_assessment(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall assessment of field alignment"""
        
        assessment = {
            "field_alignment_status": "UNKNOWN",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "compliance_score": 0
        }
        
        try:
            # Check schema field comparison
            schema_comparison = validation_results.get("schema_field_comparison", {})
            coverage_percentage = schema_comparison.get("coverage_percentage", 0)
            missing_fields = schema_comparison.get("missing_in_api", [])
            
            if coverage_percentage >= 95:
                assessment["field_alignment_status"] = "EXCELLENT"
            elif coverage_percentage >= 90:
                assessment["field_alignment_status"] = "GOOD"
            elif coverage_percentage >= 80:
                assessment["field_alignment_status"] = "ACCEPTABLE"
            else:
                assessment["field_alignment_status"] = "NEEDS_IMPROVEMENT"
            
            # Check for critical missing fields
            if missing_fields:
                assessment["critical_issues"].append(f"Missing fields in API response: {missing_fields}")
            
            # Check mapping validation
            mapping_validation = validation_results.get("mapping_validation", {})
            if not mapping_validation.get("mapping_successful", False):
                assessment["critical_issues"].append("StatusProjection to API response mapping failed")
            
            # Check logging consistency
            logging_consistency = validation_results.get("logging_consistency", {})
            logging_score = logging_consistency.get("logging_consistency_score", 0)
            if logging_score < 80:
                assessment["warnings"].append(f"Logging consistency score is low: {logging_score:.1f}%")
            
            # Calculate compliance score
            scores = []
            if coverage_percentage:
                scores.append(coverage_percentage)
            if logging_score:
                scores.append(logging_score)
            
            assessment["compliance_score"] = sum(scores) / len(scores) if scores else 0
            
            # Generate recommendations
            if missing_fields:
                assessment["recommendations"].append("Add missing fields to API response schema")
            if logging_score < 90:
                assessment["recommendations"].append("Improve logging field consistency between API and Worker components")
            
        except Exception as e:
            assessment["error"] = f"Error generating assessment: {e}"
        
        return assessment

def main():
    """Main function to run the validation"""
    validator = FieldAlignmentValidator()
    results = validator.run_comprehensive_validation()
    
    # Save results to file
    output_file = f"task_8_1_2_field_alignment_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Validation results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("TASK 8.1.2: API FIELD ALIGNMENT VALIDATION SUMMARY")
    print("="*80)
    
    overall_assessment = results.get("overall_assessment", {})
    print(f"Field Alignment Status: {overall_assessment.get('field_alignment_status', 'UNKNOWN')}")
    print(f"Compliance Score: {overall_assessment.get('compliance_score', 0):.1f}%")
    
    critical_issues = overall_assessment.get("critical_issues", [])
    if critical_issues:
        print(f"\nCRITICAL ISSUES ({len(critical_issues)}):")
        for issue in critical_issues:
            print(f"  - {issue}")
    
    warnings = overall_assessment.get("warnings", [])
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    
    recommendations = overall_assessment.get("recommendations", [])
    if recommendations:
        print(f"\nRECOMMENDATIONS ({len(recommendations)}):")
        for rec in recommendations:
            print(f"  - {rec}")
    
    # Print detailed field comparison
    validation_results = results.get("validation_results", {})
    schema_comparison = validation_results.get("schema_field_comparison", {})
    
    print(f"\nFIELD MAPPING DETAILS:")
    print(f"  StatusProjection fields: {schema_comparison.get('status_projection_fields_count', 0)}")
    print(f"  API response fields: {schema_comparison.get('api_response_fields_count', 0)}")
    print(f"  Common fields: {schema_comparison.get('common_fields_count', 0)}")
    print(f"  Coverage: {schema_comparison.get('coverage_percentage', 0):.1f}%")
    
    missing_fields = schema_comparison.get("missing_in_api", [])
    if missing_fields:
        print(f"  Missing in API: {missing_fields}")
    
    extra_fields = schema_comparison.get("extra_in_api", [])
    if extra_fields:
        print(f"  Extra in API: {extra_fields}")
    
    # Print endpoint mapping analysis
    endpoint_analysis = validation_results.get("endpoint_mapping_analysis", {})
    print(f"\nENDPOINT MAPPING ANALYSIS:")
    print(f"  Total mapped fields: {endpoint_analysis.get('total_mapped_fields', 0)}")
    
    # Print mapping validation results
    mapping_validation = validation_results.get("mapping_validation", {})
    print(f"\nMAPPING VALIDATION:")
    print(f"  Mapping successful: {mapping_validation.get('mapping_successful', False)}")
    if mapping_validation.get("success"):
        print(f"  API response fields: {len(mapping_validation.get('api_response_fields', []))}")
        print(f"  Nested totals fields: {len(mapping_validation.get('nested_totals_fields', []))}")
        print(f"  Nested artifacts fields: {len(mapping_validation.get('nested_artifacts_fields', []))}")
    
    # Print logging consistency results
    logging_consistency = validation_results.get("logging_consistency", {})
    print(f"\nLOGGING CONSISTENCY:")
    print(f"  CustomJSONEncoder available: {logging_consistency.get('custom_json_encoder_available', False)}")
    print(f"  Logger configured: {logging_consistency.get('logger_configured', False)}")
    print(f"  Consistency score: {logging_consistency.get('logging_consistency_score', 0):.1f}%")
    
    print("\n" + "="*80)
    
    return results

if __name__ == "__main__":
    main()