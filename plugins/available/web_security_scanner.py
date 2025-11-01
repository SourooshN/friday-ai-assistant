"""
Web Security Scanner Plugin for Friday AI Assistant
OWASP-style web application security testing for authorized targets only.
"""

import json
import socket
import ssl
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests

from core.logging import get_logger, initialize_logger


class WebSecurityScannerPlugin:
    """Plugin for web application security scanning."""

    def __init__(self):
        self.name = "web_security_scanner"
        self.description = "Web application security scanning and OWASP testing"
        self.version = "1.0.0"

        # Graceful logger initialization with fallback
        try:
            self.logger = get_logger()
        except RuntimeError:
            # Logger not initialized, use lazy initialization
            try:
                # Try to initialize with minimal config for testing
                initialize_logger(level="INFO", console=True, file=False)
                self.logger = get_logger()
            except Exception:
                # Ultimate fallback - create a basic logger
                import logging

                self.logger = logging.getLogger(self.name)
                self.logger.setLevel(logging.INFO)
                if not self.logger.handlers:
                    handler = logging.StreamHandler()
                    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                    handler.setFormatter(formatter)
                    self.logger.addHandler(handler)

        # Security directories
        self.web_scans_dir = Path("./data/security_ops/web_scans")
        self.web_reports_dir = Path("./data/security_ops/web_reports")

        # Create directories
        for dir_path in [self.web_scans_dir, self.web_reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Friday-Security-Scanner/1.0 (Defensive Testing)"})

        # OWASP Top 10 test patterns
        self.owasp_tests = {
            "sql_injection": {
                "payloads": ["'", '"', "1' OR '1'='1", "'; DROP TABLE users; --"],
                "indicators": ["sql", "mysql", "oracle", "error", "syntax"],
            },
            "xss": {"payloads": ["<script>alert('xss')</script>", "<img src=x onerror=alert(1)>"], "indicators": ["<script>", "alert", "onerror"]},
            "path_traversal": {
                "payloads": ["../../../etc/passwd", "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"],
                "indicators": ["root:", "windows", "system32"],
            },
            "command_injection": {"payloads": ["; ls", "| whoami", "&& dir"], "indicators": ["bin", "usr", "root", "volume"]},
        }

    async def initialize(self) -> bool:
        """Initialize the web security scanner plugin."""
        try:
            self.logger.info("Initializing web security scanner plugin")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize web security scanner plugin: {e}")
            return False

    def get_available_functions(self) -> List[str]:
        """Get list of available plugin functions."""
        return [
            "scan_web_application",
            "test_ssl_configuration",
            "check_security_headers",
            "scan_for_vulnerabilities",
            "test_authentication",
            "directory_enumeration",
            "form_security_test",
            "cookie_security_analysis",
            "generate_web_security_report",
            "validate_web_target",
        ]

    def validate_web_target(self, url: str) -> Dict[str, Any]:
        """Validate that a web target is authorized for testing."""
        try:
            # Parse URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {"success": False, "error": "Invalid URL format"}

            # Check if hostname/IP is in authorized targets
            # This would integrate with the main security_ops plugin
            authorized_targets_file = Path("./data/security_ops/configs/authorized_targets.json")

            if authorized_targets_file.exists():
                with open(authorized_targets_file, "r") as f:
                    authorized_data = json.load(f)

                authorized_hosts = set()
                for entry in authorized_data:
                    if isinstance(entry, dict) and "target" in entry:
                        authorized_hosts.add(entry["target"])
                    elif isinstance(entry, str):
                        authorized_hosts.add(entry)

                # Check if host is authorized
                if parsed.netloc not in authorized_hosts and parsed.hostname not in authorized_hosts:
                    return {"success": False, "error": "Target not in authorized list"}

            return {
                "success": True,
                "url": url,
                "parsed": {"scheme": parsed.scheme, "hostname": parsed.hostname, "port": parsed.port, "path": parsed.path},
            }

        except Exception as e:
            self.logger.error(f"Target validation failed: {e}")
            return {"success": False, "error": str(e)}

    def scan_web_application(self, base_url: str, scan_depth: int = 2) -> Dict[str, Any]:
        """Perform comprehensive web application security scan."""
        try:
            # Validate target
            validation = self.validate_web_target(base_url)
            if not validation["success"]:
                return validation

            self.logger.info(f"Starting web application scan of {base_url}")

            scan_results = {
                "target": base_url,
                "scan_start": datetime.now().isoformat(),
                "scan_depth": scan_depth,
                "findings": [],
                "pages_scanned": 0,
                "vulnerabilities_found": 0,
            }

            # 1. SSL/TLS Configuration Test
            ssl_results = self.test_ssl_configuration(base_url)
            if ssl_results["success"]:
                scan_results["ssl_test"] = ssl_results["ssl_info"]
                if ssl_results["ssl_info"]["vulnerabilities"]:
                    scan_results["findings"].extend(ssl_results["ssl_info"]["vulnerabilities"])

            # 2. Security Headers Check
            headers_results = self.check_security_headers(base_url)
            if headers_results["success"]:
                scan_results["security_headers"] = headers_results["headers_analysis"]
                scan_results["findings"].extend(headers_results["headers_analysis"]["missing_headers"])

            # 3. Directory Enumeration
            dir_results = self.directory_enumeration(base_url)
            if dir_results["success"]:
                scan_results["directory_scan"] = dir_results["directories"]
                scan_results["findings"].extend(dir_results.get("sensitive_files", []))

            # 4. Vulnerability Testing
            vuln_results = self.scan_for_vulnerabilities(base_url)
            if vuln_results["success"]:
                scan_results["vulnerability_tests"] = vuln_results["test_results"]
                scan_results["findings"].extend(vuln_results["vulnerabilities"])

            # 5. Form Security Testing
            form_results = self.form_security_test(base_url)
            if form_results["success"]:
                scan_results["form_tests"] = form_results["form_analysis"]
                scan_results["findings"].extend(form_results.get("form_vulnerabilities", []))

            scan_results["scan_end"] = datetime.now().isoformat()
            scan_results["vulnerabilities_found"] = len([f for f in scan_results["findings"] if f.get("severity") in ["high", "critical"]])

            # Save scan results
            scan_file = self.web_scans_dir / f"webscan_{urlparse(base_url).hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(scan_file, "w") as f:
                json.dump(scan_results, f, indent=2)

            return {"success": True, "scan_results": scan_results, "scan_file": str(scan_file)}

        except Exception as e:
            self.logger.error(f"Web application scan failed: {e}")
            return {"success": False, "error": str(e)}

    def test_ssl_configuration(self, url: str) -> Dict[str, Any]:
        """Test SSL/TLS configuration."""
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https":
                return {
                    "success": True,
                    "ssl_info": {
                        "ssl_enabled": False,
                        "vulnerabilities": [{"type": "no_ssl", "severity": "medium", "description": "HTTPS not enforced"}],
                    },
                }

            hostname = parsed.hostname
            port = parsed.port or 443

            # Get SSL certificate info
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

            ssl_info = {
                "ssl_enabled": True,
                "certificate": {
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "version": cert.get("version"),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "serial_number": cert.get("serialNumber"),
                },
                "cipher_suite": cipher[0] if cipher else None,
                "protocol_version": version,
                "vulnerabilities": [],
            }

            # Check for common SSL vulnerabilities
            if version in ["SSLv2", "SSLv3", "TLSv1", "TLSv1.1"]:
                ssl_info["vulnerabilities"].append({"type": "weak_protocol", "severity": "high", "description": f"Weak protocol version: {version}"})

            if cipher and "RC4" in cipher[0]:
                ssl_info["vulnerabilities"].append({"type": "weak_cipher", "severity": "medium", "description": f"Weak cipher suite: {cipher[0]}"})

            return {"success": True, "ssl_info": ssl_info}

        except Exception as e:
            self.logger.error(f"SSL test failed: {e}")
            return {"success": False, "error": str(e)}

    def check_security_headers(self, url: str) -> Dict[str, Any]:
        """Check for security headers."""
        try:
            response = self.session.get(url, timeout=10)

            security_headers = {
                "Content-Security-Policy": "CSP not set",
                "X-Frame-Options": "X-Frame-Options not set",
                "X-Content-Type-Options": "X-Content-Type-Options not set",
                "Strict-Transport-Security": "HSTS not set",
                "X-XSS-Protection": "X-XSS-Protection not set",
                "Referrer-Policy": "Referrer-Policy not set",
            }

            missing_headers = []
            present_headers = {}

            for header in security_headers.keys():
                if header in response.headers:
                    present_headers[header] = response.headers[header]
                else:
                    missing_headers.append(
                        {
                            "type": "missing_security_header",
                            "severity": "medium",
                            "header": header,
                            "description": f"Missing security header: {header}",
                        }
                    )

            headers_analysis = {
                "present_headers": present_headers,
                "missing_headers": missing_headers,
                "total_checked": len(security_headers),
                "total_missing": len(missing_headers),
            }

            return {"success": True, "headers_analysis": headers_analysis}

        except Exception as e:
            self.logger.error(f"Security headers check failed: {e}")
            return {"success": False, "error": str(e)}

    def directory_enumeration(self, base_url: str, wordlist_size: str = "small") -> Dict[str, Any]:
        """Enumerate directories and files."""
        try:
            # Common directories/files to check
            wordlists = {
                "small": [
                    "admin",
                    "login",
                    "wp-admin",
                    "administrator",
                    "phpmyadmin",
                    "robots.txt",
                    "sitemap.xml",
                    ".htaccess",
                    "web.config",
                    "backup",
                    "test",
                    "dev",
                    "staging",
                ],
                "medium": [
                    "admin",
                    "login",
                    "wp-admin",
                    "administrator",
                    "phpmyadmin",
                    "robots.txt",
                    "sitemap.xml",
                    ".htaccess",
                    "web.config",
                    "backup",
                    "test",
                    "dev",
                    "staging",
                    "api",
                    "docs",
                    "uploads",
                    "images",
                    "files",
                    "download",
                    "temp",
                ],
            }

            wordlist = wordlists.get(wordlist_size, wordlists["small"])
            found_directories = []
            sensitive_files = []

            for item in wordlist:
                try:
                    test_url = urljoin(base_url, item)
                    response = self.session.get(test_url, timeout=5, allow_redirects=False)

                    if response.status_code in [200, 301, 302, 403]:
                        found_item = {
                            "url": test_url,
                            "status_code": response.status_code,
                            "content_length": len(response.content),
                            "content_type": response.headers.get("Content-Type", "unknown"),
                        }

                        found_directories.append(found_item)

                        # Check for sensitive files
                        if item in ["robots.txt", ".htaccess", "web.config", "backup"]:
                            sensitive_files.append(
                                {
                                    "type": "sensitive_file",
                                    "severity": "low",
                                    "url": test_url,
                                    "description": f"Potentially sensitive file exposed: {item}",
                                }
                            )

                except requests.RequestException:
                    pass  # Ignore connection errors for individual requests

            return {"success": True, "directories": found_directories, "sensitive_files": sensitive_files, "total_found": len(found_directories)}

        except Exception as e:
            self.logger.error(f"Directory enumeration failed: {e}")
            return {"success": False, "error": str(e)}

    def scan_for_vulnerabilities(self, url: str) -> Dict[str, Any]:
        """Scan for common web vulnerabilities."""
        try:
            test_results = {}
            vulnerabilities = []

            for vuln_type, test_config in self.owasp_tests.items():
                test_results[vuln_type] = []

                for payload in test_config["payloads"]:
                    try:
                        # Test GET parameter
                        test_url = f"{url}?test={payload}"
                        response = self.session.get(test_url, timeout=10)

                        # Check for vulnerability indicators in response
                        response_text = response.text.lower()
                        for indicator in test_config["indicators"]:
                            if indicator in response_text:
                                vulnerability = {
                                    "type": vuln_type,
                                    "severity": "high" if vuln_type in ["sql_injection", "command_injection"] else "medium",
                                    "url": test_url,
                                    "payload": payload,
                                    "indicator": indicator,
                                    "description": f"Potential {vuln_type.replace('_', ' ')} vulnerability detected",
                                }
                                vulnerabilities.append(vulnerability)
                                test_results[vuln_type].append(vulnerability)
                                break

                    except requests.RequestException:
                        pass  # Ignore individual request errors

            return {"success": True, "test_results": test_results, "vulnerabilities": vulnerabilities, "total_vulnerabilities": len(vulnerabilities)}

        except Exception as e:
            self.logger.error(f"Vulnerability scan failed: {e}")
            return {"success": False, "error": str(e)}

    def form_security_test(self, url: str) -> Dict[str, Any]:
        """Test forms for security issues."""
        try:
            response = self.session.get(url, timeout=10)

            # Simple form detection (in a real implementation, would use BeautifulSoup)
            forms_found = response.text.count("<form")
            input_fields = response.text.count("<input")

            form_analysis = {
                "forms_detected": forms_found,
                "input_fields": input_fields,
                "csrf_protection": "token" in response.text.lower() or "csrf" in response.text.lower(),
                "method_analysis": {
                    "post_forms": response.text.lower().count('method="post"'),
                    "get_forms": response.text.lower().count('method="get"'),
                },
            }

            form_vulnerabilities = []

            # Check for potential issues
            if forms_found > 0 and not form_analysis["csrf_protection"]:
                form_vulnerabilities.append(
                    {"type": "missing_csrf_protection", "severity": "medium", "description": "Forms may be missing CSRF protection"}
                )

            if form_analysis["method_analysis"]["get_forms"] > 0:
                form_vulnerabilities.append(
                    {"type": "insecure_form_method", "severity": "low", "description": "Forms using GET method may expose sensitive data in URLs"}
                )

            return {"success": True, "form_analysis": form_analysis, "form_vulnerabilities": form_vulnerabilities}

        except Exception as e:
            self.logger.error(f"Form security test failed: {e}")
            return {"success": False, "error": str(e)}

    def cookie_security_analysis(self, url: str) -> Dict[str, Any]:
        """Analyze cookie security configuration."""
        try:
            response = self.session.get(url, timeout=10)

            cookie_analysis = {"cookies_found": len(response.cookies), "cookie_details": [], "security_issues": []}

            for cookie in response.cookies:
                cookie_info = {
                    "name": cookie.name,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": cookie.secure,
                    "httponly": hasattr(cookie, "_rest") and "HttpOnly" in cookie._rest,
                    "samesite": None,  # Would need more detailed parsing
                }

                cookie_analysis["cookie_details"].append(cookie_info)

                # Check for security issues
                if not cookie_info["secure"] and urlparse(url).scheme == "https":
                    cookie_analysis["security_issues"].append(
                        {
                            "type": "insecure_cookie",
                            "severity": "medium",
                            "cookie": cookie.name,
                            "description": f"Cookie '{cookie.name}' not marked as secure",
                        }
                    )

                if not cookie_info["httponly"]:
                    cookie_analysis["security_issues"].append(
                        {
                            "type": "missing_httponly",
                            "severity": "low",
                            "cookie": cookie.name,
                            "description": f"Cookie '{cookie.name}' not marked as HttpOnly",
                        }
                    )

            return {"success": True, "cookie_analysis": cookie_analysis}

        except Exception as e:
            self.logger.error(f"Cookie analysis failed: {e}")
            return {"success": False, "error": str(e)}

    def generate_web_security_report(self, scan_files: List[str]) -> Dict[str, Any]:
        """Generate comprehensive web security report."""
        try:
            self.logger.info("Generating web security report")

            all_findings = []
            scan_summary = {
                "total_web_scans": 0,
                "targets_scanned": set(),
                "total_vulnerabilities": 0,
                "high_risk_findings": 0,
                "ssl_issues": 0,
                "header_issues": 0,
            }

            # Process scan files
            for scan_file in scan_files:
                try:
                    with open(scan_file, "r") as f:
                        scan_data = json.load(f)

                    scan_summary["total_web_scans"] += 1
                    scan_summary["targets_scanned"].add(scan_data.get("target", "unknown"))

                    # Process findings
                    for finding in scan_data.get("findings", []):
                        all_findings.append(finding)
                        scan_summary["total_vulnerabilities"] += 1

                        if finding.get("severity") in ["high", "critical"]:
                            scan_summary["high_risk_findings"] += 1

                        if finding.get("type") in ["weak_protocol", "weak_cipher"]:
                            scan_summary["ssl_issues"] += 1
                        elif finding.get("type") == "missing_security_header":
                            scan_summary["header_issues"] += 1

                except Exception as e:
                    self.logger.warning(f"Could not process web scan file {scan_file}: {e}")

            scan_summary["targets_scanned"] = list(scan_summary["targets_scanned"])

            # Generate report
            report_content = self._generate_web_security_report_content(scan_summary, all_findings)

            # Save report
            report_file = self.web_reports_dir / f"web_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_file, "w") as f:
                f.write(report_content)

            return {"success": True, "report_file": str(report_file), "summary": scan_summary, "findings_count": len(all_findings)}

        except Exception as e:
            self.logger.error(f"Failed to generate web security report: {e}")
            return {"success": False, "error": str(e)}

    def _generate_web_security_report_content(self, summary: Dict, findings: List[Dict]) -> str:
        """Generate web security report content in Markdown."""
        report = f"""# Web Application Security Assessment Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report details the web application security assessment conducted on authorized targets using OWASP-based testing methodologies.

### Assessment Overview
- **Web Applications Scanned**: {summary['total_web_scans']}
- **Targets Assessed**: {len(summary['targets_scanned'])}
- **Total Vulnerabilities**: {summary['total_vulnerabilities']}
- **High-Risk Findings**: {summary['high_risk_findings']}
- **SSL/TLS Issues**: {summary['ssl_issues']}
- **Security Header Issues**: {summary['header_issues']}

### Targets Assessed
"""
        for target in summary["targets_scanned"]:
            report += f"- {target}\n"

        report += "\n## Vulnerability Breakdown\n\n"

        # Group findings by type
        vuln_by_type = {}
        for finding in findings:
            vuln_type = finding.get("type", "unknown")
            if vuln_type not in vuln_by_type:
                vuln_by_type[vuln_type] = []
            vuln_by_type[vuln_type].append(finding)

        for vuln_type, vulns in vuln_by_type.items():
            if vulns:
                report += f"\n### {vuln_type.replace('_', ' ').title()} ({len(vulns)} findings)\n"
                for vuln in vulns[:3]:  # Show top 3 of each type
                    severity = vuln.get("severity", "unknown")
                    description = vuln.get("description", "No description")
                    report += f"- **{severity.upper()}**: {description}\n"

        report += "\n## OWASP Top 10 Assessment\n\n"
        report += "The following OWASP Top 10 categories were assessed:\n\n"
        report += "1. **Injection** - SQL, NoSQL, OS, and LDAP injection\n"
        report += "2. **Broken Authentication** - Authentication and session management\n"
        report += "3. **Sensitive Data Exposure** - Data protection in transit and at rest\n"
        report += "4. **XML External Entities (XXE)** - XML processors vulnerabilities\n"
        report += "5. **Broken Access Control** - Authorization failures\n"
        report += "6. **Security Misconfiguration** - Default configurations and security headers\n"
        report += "7. **Cross-Site Scripting (XSS)** - Client-side injection vulnerabilities\n"
        report += "8. **Insecure Deserialization** - Serialization vulnerabilities\n"
        report += "9. **Using Components with Known Vulnerabilities** - Outdated components\n"
        report += "10. **Insufficient Logging & Monitoring** - Detection and response capabilities\n"

        report += "\n## Remediation Recommendations\n\n"
        report += "### Immediate Actions Required\n"
        report += "1. **Address Critical/High Vulnerabilities**: Prioritize fixing all critical and high-severity findings\n"
        report += "2. **Implement Security Headers**: Add missing security headers to prevent common attacks\n"
        report += "3. **SSL/TLS Configuration**: Update SSL/TLS configuration to use secure protocols and ciphers\n"
        report += "4. **Input Validation**: Implement proper input validation and sanitization\n"

        report += "\n### Long-term Security Improvements\n"
        report += "1. **Security by Design**: Integrate security considerations into development lifecycle\n"
        report += "2. **Regular Security Testing**: Implement automated security testing in CI/CD pipeline\n"
        report += "3. **Security Training**: Provide security awareness training for development teams\n"
        report += "4. **Incident Response**: Establish security incident response procedures\n"

        report += "\n## Compliance and Standards\n\n"
        report += "This assessment was conducted in accordance with:\n"
        report += "- OWASP Web Security Testing Guide\n"
        report += "- NIST Cybersecurity Framework\n"
        report += "- Industry best practices for web application security\n"

        report += "\n## Disclaimer\n\n"
        report += "This security assessment was conducted on authorized targets only using defensive security testing methods. "
        report += "All findings should be verified and remediated according to organizational security policies and procedures. "
        report += "This assessment does not guarantee the absence of all security vulnerabilities.\n"

        return report

    async def cleanup(self):
        """Clean up web security scanner resources."""
        self.session.close()
        self.logger.info("Web security scanner plugin cleanup completed")


# Plugin instance - commented out to avoid logger initialization issues during import
# plugin = WebSecurityScannerPlugin()
