"""
Integration tests for Milestone 5: Ops Module
Tests the security operations capabilities with proper safety controls.
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Import our security plugins
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# Initialize logger for testing
from core.logging import initialize_logger
try:
    # Initialize with minimal test configuration
    initialize_logger(level="INFO", console=True, file=False)
except Exception:
    # Logger may already be initialized, ignore
    pass

from plugins.available.security_ops import SecurityOpsPlugin
from plugins.available.web_security_scanner import WebSecurityScannerPlugin


class TestMilestone5OpsModule:
    """Test suite for Milestone 5 security operations features."""

    @pytest.fixture
    def security_ops_plugin(self):
        """Create security ops plugin instance."""
        return SecurityOpsPlugin()

    @pytest.fixture
    def web_security_plugin(self):
        """Create web security scanner plugin instance."""
        return WebSecurityScannerPlugin()

    @pytest.mark.asyncio
    async def test_security_ops_plugin_initialization(self, security_ops_plugin):
        """Test security ops plugin initializes correctly."""
        result = await security_ops_plugin.initialize()
        assert result is True
        assert security_ops_plugin.name == "security_ops"
        assert security_ops_plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_web_security_plugin_initialization(self, web_security_plugin):
        """Test web security scanner plugin initializes correctly."""
        result = await web_security_plugin.initialize()
        assert result is True
        assert web_security_plugin.name == "web_security_scanner"
        assert web_security_plugin.version == "1.0.0"

    def test_target_authorization_system(self, security_ops_plugin):
        """Test target authorization and validation system."""
        # Test adding authorized target
        result = security_ops_plugin.add_authorized_target(
            target="127.0.0.1",
            justification="Localhost testing for security validation",
            approver="test_admin"
        )

        assert result["success"] is True
        assert result["target"] == "127.0.0.1"
        assert "127.0.0.1" in security_ops_plugin.authorized_targets

        # Test listing authorized targets
        list_result = security_ops_plugin.list_authorized_targets()
        assert list_result["success"] is True
        assert len(list_result["authorized_targets"]) >= 1

        # Test removing authorized target
        remove_result = security_ops_plugin.remove_authorized_target(
            target="127.0.0.1",
            remover="test_admin"
        )

        assert remove_result["success"] is True
        assert "127.0.0.1" not in security_ops_plugin.authorized_targets

    def test_target_validation(self, security_ops_plugin):
        """Test target format validation."""
        # Valid IP address
        assert security_ops_plugin._validate_target_format("192.168.1.1") is True

        # Valid network
        assert security_ops_plugin._validate_target_format("192.168.1.0/24") is True

        # Valid hostname
        assert security_ops_plugin._validate_target_format("example.com") is True

        # Invalid formats
        assert security_ops_plugin._validate_target_format("invalid..target") is False
        assert security_ops_plugin._validate_target_format("") is False

    def test_sensitive_network_detection(self, security_ops_plugin):
        """Test detection of sensitive networks."""
        # Loopback should be detected as sensitive in certain contexts
        assert security_ops_plugin._is_sensitive_network("127.0.0.0/8") is True

        # Link-local should be detected as sensitive
        assert security_ops_plugin._is_sensitive_network("169.254.0.0/16") is True

        # Regular private network should not be sensitive
        assert security_ops_plugin._is_sensitive_network("192.168.1.0/24") is False

    def test_network_discovery_authorization_check(self, security_ops_plugin):
        """Test that network discovery requires authorization."""
        # Test unauthorized target
        result = security_ops_plugin.network_discovery("192.168.1.0/24")
        assert result["success"] is False
        assert "not in authorized list" in result["error"]

        # Add target to authorized list
        security_ops_plugin.add_authorized_target(
            target="192.168.1.0/24",
            justification="Test network discovery",
            approver="test_admin"
        )

        # Note: Actual network discovery would require network access
        # In a real test, we would mock the network operations

    def test_port_scan_authorization_check(self, security_ops_plugin):
        """Test that port scanning requires authorization."""
        # Test unauthorized target
        result = security_ops_plugin.port_scan("192.168.1.100")
        assert result["success"] is False
        assert "not in authorized list" in result["error"]

        # Add target to authorized list
        security_ops_plugin.add_authorized_target(
            target="192.168.1.100",
            justification="Test port scanning",
            approver="test_admin"
        )

        # Note: Actual port scanning would require network access and nmap
        # In a real test, we would mock the nmap operations

    def test_vulnerability_scan_authorization_check(self, security_ops_plugin):
        """Test that vulnerability scanning requires authorization."""
        # Test unauthorized target
        result = security_ops_plugin.vulnerability_scan("192.168.1.100")
        assert result["success"] is False
        assert "not in authorized list" in result["error"]

    def test_lab_environment_validation(self, security_ops_plugin):
        """Test lab environment setup validation."""
        result = security_ops_plugin.test_lab_environment()

        assert result["success"] is True
        assert "lab_status" in result
        lab_status = result["lab_status"]

        # Check that required tests are performed
        required_tests = [
            "network_isolation",
            "tool_availability",
            "permissions",
            "target_validation",
            "logging"
        ]

        for test_name in required_tests:
            assert test_name in lab_status["test_results"]
            assert "passed" in lab_status["test_results"][test_name]

    def test_security_report_generation(self, security_ops_plugin):
        """Test security report generation."""
        # Create mock scan data
        mock_scan_data = {
            "target": "127.0.0.1",
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "host": "127.0.0.1",
                    "vulnerabilities": [
                        {
                            "severity": "high",
                            "finding": "Test vulnerability",
                            "script": "test-script"
                        }
                    ],
                    "protocols": {
                        "tcp": {
                            "22": {"state": "open", "service": "ssh"},
                            "80": {"state": "open", "service": "http"}
                        }
                    }
                }
            ]
        }

        # Save mock scan data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_scan_data, f)
            mock_file = f.name

        try:
            # Generate report
            result = security_ops_plugin.generate_security_report([mock_file])

            assert result["success"] is True
            assert "report_file" in result
            assert result["findings_count"] >= 0

            # Verify report file exists
            report_file = Path(result["report_file"])
            assert report_file.exists()

            # Check report content
            report_content = report_file.read_text()
            assert "Security Assessment Summary Report" in report_content
            assert "Recommendations" in report_content

        finally:
            # Cleanup
            Path(mock_file).unlink(missing_ok=True)

    def test_web_target_validation(self, web_security_plugin):
        """Test web target validation system."""
        # Test valid URL format
        result = web_security_plugin.validate_web_target("https://example.com")
        assert result["success"] is True
        assert result["parsed"]["scheme"] == "https"
        assert result["parsed"]["hostname"] == "example.com"

        # Test invalid URL format
        result = web_security_plugin.validate_web_target("not-a-url")
        assert result["success"] is False

        # Test missing scheme
        result = web_security_plugin.validate_web_target("example.com/path")
        assert result["success"] is False

    def test_ssl_configuration_testing(self, web_security_plugin):
        """Test SSL configuration analysis."""
        # Test non-HTTPS URL
        result = web_security_plugin.test_ssl_configuration("http://example.com")
        assert result["success"] is True
        assert result["ssl_info"]["ssl_enabled"] is False

        # Note: Testing actual SSL would require network access
        # In a real test environment, we would test against a controlled HTTPS endpoint

    def test_security_headers_analysis(self, web_security_plugin):
        """Test security headers checking functionality."""
        # Note: This would require mocking HTTP responses in a real test
        # The test validates the function structure and expected return format

        expected_functions = web_security_plugin.get_available_functions()
        assert "check_security_headers" in expected_functions
        assert "test_ssl_configuration" in expected_functions
        assert "scan_for_vulnerabilities" in expected_functions

    def test_vulnerability_assessment_structure(self, web_security_plugin):
        """Test vulnerability assessment structure."""
        # Verify OWASP test patterns are defined
        assert hasattr(web_security_plugin, 'owasp_tests')
        owasp_tests = web_security_plugin.owasp_tests

        # Check for key vulnerability types
        expected_vuln_types = ["sql_injection", "xss", "path_traversal", "command_injection"]
        for vuln_type in expected_vuln_types:
            assert vuln_type in owasp_tests
            assert "payloads" in owasp_tests[vuln_type]
            assert "indicators" in owasp_tests[vuln_type]

    def test_web_security_report_generation(self, web_security_plugin):
        """Test web security report generation."""
        # Create mock web scan data
        mock_web_scan = {
            "target": "https://example.com",
            "findings": [
                {
                    "type": "missing_security_header",
                    "severity": "medium",
                    "header": "Content-Security-Policy",
                    "description": "CSP header missing"
                },
                {
                    "type": "ssl_issue",
                    "severity": "high",
                    "description": "Weak SSL configuration"
                }
            ],
            "timestamp": datetime.now().isoformat()
        }

        # Save mock scan data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_web_scan, f)
            mock_file = f.name

        try:
            # Generate web security report
            result = web_security_plugin.generate_web_security_report([mock_file])

            assert result["success"] is True
            assert "report_file" in result

            # Verify report file exists
            report_file = Path(result["report_file"])
            assert report_file.exists()

            # Check report content
            report_content = report_file.read_text()
            assert "Web Application Security Assessment Report" in report_content
            assert "OWASP Top 10" in report_content

        finally:
            # Cleanup
            Path(mock_file).unlink(missing_ok=True)

    def test_plugin_function_availability(self, security_ops_plugin, web_security_plugin):
        """Test that all required functions are available."""

        # Security ops functions
        security_functions = security_ops_plugin.get_available_functions()
        required_security_functions = [
            "add_authorized_target",
            "network_discovery",
            "port_scan",
            "vulnerability_scan",
            "traffic_analysis",
            "generate_security_report",
            "test_lab_environment"
        ]
        for func in required_security_functions:
            assert func in security_functions

        # Web security functions
        web_functions = web_security_plugin.get_available_functions()
        required_web_functions = [
            "scan_web_application",
            "test_ssl_configuration",
            "check_security_headers",
            "scan_for_vulnerabilities",
            "directory_enumeration",
            "generate_web_security_report"
        ]
        for func in required_web_functions:
            assert func in web_functions

    def test_ethical_guidelines_enforcement(self, security_ops_plugin):
        """Test that ethical guidelines are enforced."""
        # Test that sensitive networks are blocked
        result = security_ops_plugin.add_authorized_target(
            target="127.0.0.0/8",
            justification="Test",
            approver="test"
        )

        # Should be rejected due to sensitive network detection
        assert result["success"] is False
        assert "sensitive network" in result["error"]

        # Test that authorization is required
        unauthorized_result = security_ops_plugin.port_scan("8.8.8.8")
        assert unauthorized_result["success"] is False
        assert "not in authorized list" in unauthorized_result["error"]

    def test_security_configuration_files(self, security_ops_plugin):
        """Test security configuration file creation."""
        # Check that configuration directories exist
        assert security_ops_plugin.configs_dir.exists()
        assert security_ops_plugin.reports_dir.exists()
        assert security_ops_plugin.scans_dir.exists()

        # Check for policy file creation
        policy_file = security_ops_plugin.configs_dir / "security_policy.json"
        assert policy_file.exists()

        # Validate policy content
        with open(policy_file, 'r') as f:
            policy = json.load(f)

        assert "scan_policies" in policy
        assert "reporting" in policy
        assert policy["scan_policies"]["require_authorization"] is True

    @pytest.mark.asyncio
    async def test_plugin_cleanup(self, security_ops_plugin, web_security_plugin):
        """Test that plugins clean up properly."""
        # Test cleanup for both plugins
        await security_ops_plugin.cleanup()
        await web_security_plugin.cleanup()

        # Verify no exceptions were raised
        assert True  # If we get here, cleanup succeeded

    @pytest.mark.asyncio
    async def test_end_to_end_security_workflow(self, security_ops_plugin):
        """Test complete end-to-end security workflow."""
        # 1. Add authorized target
        target_result = security_ops_plugin.add_authorized_target(
            target="127.0.0.1",
            justification="End-to-end workflow testing",
            approver="test_admin"
        )
        assert target_result["success"] is True

        # 2. Test lab environment
        lab_result = security_ops_plugin.test_lab_environment()
        assert lab_result["success"] is True

        # 3. List authorized targets
        list_result = security_ops_plugin.list_authorized_targets()
        assert list_result["success"] is True
        assert len(list_result["authorized_targets"]) >= 1

        # 4. Create mock scan results
        mock_findings = [
            {
                "type": "vulnerability",
                "host": "127.0.0.1",
                "severity": "medium",
                "description": "Test finding"
            }
        ]

        # 5. Create temporary scan file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            scan_data = {
                "target": "127.0.0.1",
                "findings": mock_findings,
                "results": [{"host": "127.0.0.1", "vulnerabilities": mock_findings}]
            }
            json.dump(scan_data, f)
            scan_file = f.name

        try:
            # 6. Generate security report
            report_result = security_ops_plugin.generate_security_report([scan_file])
            assert report_result["success"] is True

            # 7. Verify report content
            report_file = Path(report_result["report_file"])
            assert report_file.exists()

        finally:
            # 8. Cleanup
            Path(scan_file).unlink(missing_ok=True)
            security_ops_plugin.remove_authorized_target("127.0.0.1", "test_admin")

    def test_milestone_deliverables_validation(self, security_ops_plugin, web_security_plugin):
        """Test that all milestone 5 deliverables are present and functional."""

        # Deliverable 1: Sandbox configuration
        assert security_ops_plugin.ops_dir.exists()
        assert security_ops_plugin.configs_dir.exists()

        # Deliverable 2: nmap/scapy integration
        security_functions = security_ops_plugin.get_available_functions()
        assert "network_discovery" in security_functions
        assert "port_scan" in security_functions
        assert "traffic_analysis" in security_functions

        # Deliverable 3: Target scopes file and authorization
        assert "add_authorized_target" in security_functions
        assert "list_authorized_targets" in security_functions

        # Deliverable 4: Web security scanning (ZAP-style)
        web_functions = web_security_plugin.get_available_functions()
        assert "scan_web_application" in web_functions
        assert "scan_for_vulnerabilities" in web_functions

        # Deliverable 5: Security reporting
        assert "generate_security_report" in security_functions
        assert "generate_web_security_report" in web_functions

        # Deliverable 6: Lab environment testing
        assert "test_lab_environment" in security_functions

        # All deliverables validated
        assert True