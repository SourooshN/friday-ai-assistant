"""
Scanner Agent for cybersecurity operations.
Handles vulnerability scanning, security analysis, and threat detection.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import json
import subprocess
import platform
from datetime import datetime

from agents.base_agent import BaseAgent, Task, TaskType


class ScannerAgent(BaseAgent):
    """Agent specialized in security scanning and analysis."""
    
    def __init__(self, name: str, model_manager, memory, policy_engine):
        """Initialize Scanner Agent with cybersecurity capabilities."""
        capabilities = [
            "network_scanning",
            "vulnerability_assessment", 
            "security_analysis",
            "threat_detection",
            "port_scanning",
            "service_detection",
            "cybersecurity",
            "data_analysis"
        ]
        
        super().__init__(
            name=name,
            capabilities=capabilities,
            model_manager=model_manager,
            memory=memory,
            policy_engine=policy_engine
        )
        
        self.logger.info("Initialized Scanner Agent")
        
        # Tool configurations
        self.tools = {
            'nmap': self._check_tool_availability('nmap'),
            'netstat': True,  # Usually available on all systems
            'ping': True,
            'tracert': platform.system() == 'Windows',
            'traceroute': platform.system() != 'Windows'
        }
    
    async def _execute_task(self, task_data) -> Dict[str, Any]:
        """Execute scanner-specific tasks."""
        try:
            # Handle both dict and non-dict task data
            if isinstance(task_data, dict):
                description = task_data.get('description', 'Unknown task')
                task_type = task_data.get('type', 'general')
                parameters = task_data.get('parameters', {})
            else:
                # If task_data is not a dict, convert it
                description = str(task_data) if task_data else 'Unknown task'
                task_type = 'general'
                parameters = {}
            
            self.logger.info(f"Scanner Agent executing: {description}")
            
            # Route based on task type or description keywords
            description_lower = description.lower()
            
            if any(keyword in description_lower for keyword in ['scan', 'port', 'network']):
                return await self._perform_scan(description, parameters)
            elif any(keyword in description_lower for keyword in ['analyze', 'assess', 'vulnerability']):
                return await self._analyze_security(description, parameters)
            elif any(keyword in description_lower for keyword in ['threat', 'detect', 'malware']):
                return await self._detect_threats(description, parameters)
            else:
                # General information request
                return await self._provide_security_info(description, parameters)
                
        except Exception as e:
            self.logger.error(f"Scanner task failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'agent': self.name
            }
    
    async def _perform_scan(self, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform network or system scanning."""
        self.logger.info(f"Performing scan based on: {description}")
        
        try:
            # Extract target from description or parameters
            target = parameters.get('target', 'localhost')
            scan_type = parameters.get('scan_type', 'basic')
            
            # Check if we should use actual tools or simulate
            if self.policy_engine and not await self._check_scan_permission(target):
                return await self._simulate_scan(target, scan_type)
            
            # Perform actual scan (if tools available and permitted)
            results = await self._execute_scan(target, scan_type)
            
            # Analyze results
            analysis = await self._analyze_scan_results(results)
            
            return {
                'status': 'success',
                'scan_type': scan_type,
                'target': target,
                'results': results,
                'analysis': analysis,
                'recommendations': self._generate_recommendations(analysis),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Scan failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Scan operation failed'
            }
    
    async def _simulate_scan(self, target: str, scan_type: str) -> Dict[str, Any]:
        """Simulate a scan when actual scanning is not permitted."""
        self.logger.info(f"Simulating {scan_type} scan on {target}")
        
        # Use AI to generate realistic scan results
        prompt = f"""Simulate a {scan_type} security scan on {target}.
        Provide realistic but safe example results including:
        - Open ports (if network scan)
        - Running services
        - Potential vulnerabilities (non-critical examples)
        - Security recommendations
        
        Format as a structured report."""
        
        response = await self.model_manager.generate(
            prompt=prompt,
            max_tokens=800
        )
        
        return {
            'status': 'success',
            'scan_type': f'{scan_type} (simulated)',
            'target': target,
            'results': response,
            'note': 'This is a simulated scan for demonstration purposes',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_scan(self, target: str, scan_type: str) -> Dict[str, Any]:
        """Execute actual scan using available tools."""
        results = {}
        
        # Basic connectivity check
        if await self._check_connectivity(target):
            results['connectivity'] = 'Target is reachable'
        else:
            results['connectivity'] = 'Target is not reachable'
            return results
        
        # Port scan (if nmap available)
        if self.tools.get('nmap') and scan_type in ['full', 'port']:
            try:
                port_results = await self._run_port_scan(target)
                results['ports'] = port_results
            except Exception as e:
                results['ports'] = f'Port scan failed: {str(e)}'
        
        # Service detection
        if scan_type in ['full', 'service']:
            try:
                services = await self._detect_services(target)
                results['services'] = services
            except Exception as e:
                results['services'] = f'Service detection failed: {str(e)}'
        
        return results
    
    async def _check_connectivity(self, target: str) -> bool:
        """Check if target is reachable."""
        try:
            cmd = ['ping', '-n', '1', target] if platform.system() == 'Windows' else ['ping', '-c', '1', target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _run_port_scan(self, target: str) -> List[Dict[str, Any]]:
        """Run port scan using nmap."""
        # For safety, only scan common ports
        common_ports = "21,22,23,25,53,80,110,443,445,3306,3389,8080"
        
        try:
            cmd = ['nmap', '-p', common_ports, '-sV', target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Parse nmap output (simplified)
            open_ports = []
            for line in result.stdout.split('\n'):
                if '/tcp' in line and 'open' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        port_info = {
                            'port': parts[0].split('/')[0],
                            'state': parts[1],
                            'service': ' '.join(parts[2:]) if len(parts) > 2 else 'unknown'
                        }
                        open_ports.append(port_info)
            
            return open_ports
        except Exception as e:
            self.logger.error(f"Port scan error: {str(e)}")
            return []
    
    async def _detect_services(self, target: str) -> Dict[str, Any]:
        """Detect running services on target."""
        # This is a placeholder - actual implementation would vary by OS
        return {
            'method': 'basic detection',
            'services': ['HTTP', 'SSH', 'DNS'],  # Example services
            'note': 'Service detection requires appropriate permissions'
        }
    
    async def _analyze_scan_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze scan results for security issues."""
        analysis = {
            'risk_level': 'low',
            'vulnerabilities': [],
            'observations': []
        }
        
        # Analyze open ports
        if 'ports' in results and isinstance(results['ports'], list):
            for port_info in results['ports']:
                port = port_info.get('port', '')
                service = port_info.get('service', '')
                
                # Check for potentially risky ports
                risky_ports = {
                    '21': 'FTP - Often unencrypted',
                    '23': 'Telnet - Unencrypted protocol',
                    '445': 'SMB - Often targeted by attackers',
                    '3389': 'RDP - Remote access risk'
                }
                
                if port in risky_ports:
                    analysis['vulnerabilities'].append({
                        'port': port,
                        'service': service,
                        'risk': risky_ports[port]
                    })
                    analysis['risk_level'] = 'medium'
        
        # Add general observations
        if results.get('connectivity') == 'Target is reachable':
            analysis['observations'].append('Target responds to ping requests')
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on analysis."""
        recommendations = []
        
        if analysis.get('risk_level') in ['medium', 'high']:
            recommendations.append("Review and close unnecessary open ports")
            
        for vuln in analysis.get('vulnerabilities', []):
            if 'FTP' in vuln.get('risk', ''):
                recommendations.append("Consider using SFTP or FTPS instead of FTP")
            elif 'Telnet' in vuln.get('risk', ''):
                recommendations.append("Replace Telnet with SSH for secure remote access")
            elif 'SMB' in vuln.get('risk', ''):
                recommendations.append("Ensure SMB is properly configured and patched")
            elif 'RDP' in vuln.get('risk', ''):
                recommendations.append("Use VPN for RDP access and enable Network Level Authentication")
        
        if not recommendations:
            recommendations.append("Continue regular security monitoring")
            recommendations.append("Keep all services and systems updated")
        
        return recommendations
    
    async def _analyze_security(self, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security analysis."""
        prompt = f"""As a cybersecurity expert, analyze: {description}
        
        Provide:
        1. Security assessment
        2. Potential risks
        3. Mitigation strategies
        4. Best practices
        
        Be specific and actionable."""
        
        response = await self.model_manager.generate(
            prompt=prompt,
            max_tokens=600
        )
        
        return {
            'status': 'success',
            'analysis_type': 'security assessment',
            'results': response,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _detect_threats(self, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential security threats."""
        prompt = f"""As a threat detection specialist, analyze: {description}
        
        Identify:
        1. Potential threat indicators
        2. Attack vectors
        3. Risk assessment
        4. Recommended actions
        
        Focus on practical detection and prevention."""
        
        response = await self.model_manager.generate(
            prompt=prompt,
            max_tokens=600
        )
        
        return {
            'status': 'success',
            'detection_type': 'threat analysis',
            'results': response,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _provide_security_info(self, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Provide security information and guidance."""
        prompt = f"""As a cybersecurity expert, provide helpful information about: {description}
        
        Include practical advice and best practices where relevant."""
        
        response = await self.model_manager.generate(
            prompt=prompt,
            max_tokens=500
        )
        
        return {
            'status': 'success',
            'info_type': 'security guidance',
            'response': response,
            'agent': self.name,
            'capabilities': self.capabilities
        }
    
    def _check_tool_availability(self, tool: str) -> bool:
        """Check if a security tool is available on the system."""
        try:
            subprocess.run([tool, '--version'], capture_output=True, timeout=2)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    async def _check_scan_permission(self, target: str) -> bool:
        """Check if scanning the target is allowed by policy."""
        # Always allow localhost and private IPs
        safe_targets = ['localhost', '127.0.0.1', '::1']
        
        if target in safe_targets:
            return True
        
        # Check if it's a private IP
        if self._is_private_ip(target):
            return True
        
        # For other targets, check policy
        # For now, we'll be conservative and not scan external targets
        return False
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP address is in private range."""
        private_ranges = [
            '10.',
            '172.16.', '172.17.', '172.18.', '172.19.',
            '172.20.', '172.21.', '172.22.', '172.23.',
            '172.24.', '172.25.', '172.26.', '172.27.',
            '172.28.', '172.29.', '172.30.', '172.31.',
            '192.168.'
        ]
        
        return any(ip.startswith(range) for range in private_ranges)