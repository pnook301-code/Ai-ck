#!/usr/bin/env python3
"""
Security Audit System for CK-NEXUS
Checks for vulnerabilities and security issues
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """Security issue found."""
    file: str
    line: int
    issue: str
    severity: str  # critical, high, medium, low
    recommendation: str


class SecurityAuditor:
    """Security auditor for code and configuration."""
    
    def __init__(self):
        self.issues: List[SecurityIssue] = []
        
        # Dangerous patterns
        self.dangerous_patterns = [
            (r'eval\s*\(', 'Use of eval()', 'critical', 'Avoid eval(), use ast.literal_eval()'),
            (r'exec\s*\(', 'Use of exec()', 'critical', 'Avoid exec()'),
            (r'os\.system\s*\(', 'Use of os.system()', 'high', 'Use subprocess.run() instead'),
            (r'subprocess\.call\s*\(.*shell\s*=\s*True', 'Shell injection risk', 'critical', 'Use shell=False'),
            (r'__import__\s*\(', 'Dynamic import', 'medium', 'Use static imports'),
            (r'pickle\.loads?\s*\(', 'Pickle deserialization', 'critical', 'Avoid pickle with untrusted data'),
            (r'yaml\.load\s*\([^)]*\)', 'Unsafe YAML load', 'high', 'Use yaml.safe_load()'),
            (r'verify\s*=\s*False', 'SSL verification disabled', 'high', 'Enable SSL verification'),
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password', 'critical', 'Use environment variables'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key', 'high', 'Use environment variables'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret', 'critical', 'Use environment variables'),
        ]
    
    def audit_file(self, filepath: str) -> List[SecurityIssue]:
        """Audit a single file."""
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                for pattern, issue_name, severity, recommendation in self.dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(SecurityIssue(
                            file=filepath,
                            line=i,
                            issue=issue_name,
                            severity=severity,
                            recommendation=recommendation
                        ))
        except Exception as e:
            pass
        
        return issues
    
    def audit_directory(self, directory: str, extensions: Tuple[str] = ('.py', '.js', '.ts')) -> List[SecurityIssue]:
        """Audit all files in a directory."""
        all_issues = []
        
        for root, dirs, files in os.walk(directory):
            # Skip hidden dirs and common non-code dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    filepath = os.path.join(root, file)
                    issues = self.audit_file(filepath)
                    all_issues.extend(issues)
        
        self.issues = all_issues
        return all_issues
    
    def audit_config(self, config_path: str) -> List[SecurityIssue]:
        """Audit configuration file."""
        issues = []
        
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Check for exposed secrets
            for key, value in config.items():
                if isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, str) and len(v) > 10:
                            if any(word in k.lower() for word in ['key', 'secret', 'password', 'token']):
                                issues.append(SecurityIssue(
                                    file=config_path,
                                    line=0,
                                    issue=f"Exposed {k} in config",
                                    severity="high",
                                    recommendation="Store in environment variables or encrypted storage"
                                ))
        except Exception as e:
            pass
        
        return issues
    
    def get_report(self) -> Dict:
        """Generate security report."""
        critical = [i for i in self.issues if i.severity == "critical"]
        high = [i for i in self.issues if i.severity == "high"]
        medium = [i for i in self.issues if i.severity == "medium"]
        low = [i for i in self.issues if i.severity == "low"]
        
        return {
            "total_issues": len(self.issues),
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "issues": [
                {
                    "file": i.file,
                    "line": i.line,
                    "issue": i.issue,
                    "severity": i.severity,
                    "recommendation": i.recommendation
                }
                for i in self.issues[:20]  # Top 20 issues
            ]
        }


class VulnerabilityScanner:
    """Scan for common vulnerabilities."""
    
    def __init__(self):
        self.vulnerabilities = []
    
    def scan_dependencies(self, requirements_file: str) -> List[Dict]:
        """Scan dependencies for known vulnerabilities."""
        vulns = []
        
        try:
            with open(requirements_file) as f:
                packages = [line.strip().split('==')[0].lower() for line in f if line.strip() and not line.startswith('#')]
            
            # Known vulnerable packages (simplified)
            known_vulnerable = {
                'requests': {'fixed': '2.31.0', 'cve': 'CVE-2023-32681'},
                'flask': {'fixed': '2.3.2', 'cve': 'CVE-2023-30861'},
                'django': {'fixed': '4.2.4', 'cve': 'CVE-2023-31047'},
            }
            
            for pkg in packages:
                if pkg in known_vulnerable:
                    vulns.append({
                        "package": pkg,
                        "vulnerability": known_vulnerable[pkg]['cve'],
                        "fixed_version": known_vulnerable[pkg]['fixed']
                    })
        except FileNotFoundError:
            pass
        
        return vulns
    
    def scan_secrets(self, directory: str) -> List[Dict]:
        """Scan for exposed secrets."""
        secrets = []
        
        secret_patterns = [
            (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']([^"\']{20,})["\']', 'API Key'),
            (r'(?:secret|password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']', 'Secret/Password'),
            (r'(?:token|access[_-]?token)\s*[=:]\s*["\']([^"\']{20,})["\']', 'Token'),
            (r'(?:AWS|aws)[_(?:ACCESSKEYID|secret_access_key)]\s*[=:]\s*["\']([^"\']{20,})["\']', 'AWS Credential'),
        ]
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        for pattern, secret_type in secret_patterns:
                            matches = re.findall(pattern, content)
                            for match in matches:
                                if len(match) > 10:  # Skip short strings
                                    secrets.append({
                                        "file": filepath,
                                        "type": secret_type,
                                        "preview": match[:10] + "..."
                                    })
                    except Exception:
                        pass
        
        return secrets


def run_full_audit(directory: str = None) -> Dict:
    """Run full security audit."""
    directory = directory or os.path.dirname(os.path.abspath(__file__))
    
    print("🔒 RUNNING SECURITY AUDIT")
    print("=" * 60)
    
    # Code audit
    auditor = SecurityAuditor()
    issues = auditor.audit_directory(directory)
    report = auditor.get_report()
    
    print(f"\n📊 Code Issues: {report['total_issues']}")
    print(f"   🔴 Critical: {report['critical']}")
    print(f"   🟠 High: {report['high']}")
    print(f"   🟡 Medium: {report['medium']}")
    print(f"   🟢 Low: {report['low']}")
    
    # Vulnerability scan
    scanner = VulnerabilityScanner()
    secrets = scanner.scan_secrets(directory)
    
    print(f"\n🔑 Exposed Secrets: {len(secrets)}")
    for s in secrets[:5]:
        print(f"   ⚠️ {s['type']} in {s['file']}")
    
    # Config audit
    config_path = os.path.expanduser("~/.ck-nexus/config.json")
    if os.path.exists(config_path):
        config_issues = auditor.audit_config(config_path)
        print(f"\n⚙️ Config Issues: {len(config_issues)}")
    
    print("\n" + "=" * 60)
    
    return {
        "code_report": report,
        "secrets": secrets,
        "config_issues": len(config_issues) if os.path.exists(config_path) else 0
    }


if __name__ == "__main__":
    result = run_full_audit("/workspace/ck-nexus")
    print(json.dumps(result, indent=2))
