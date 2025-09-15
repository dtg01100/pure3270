import xml.etree.ElementTree as ET
import json
import re
from pathlib import Path
from typing import List, Dict, Optional


def parse_junit_failures(
    junit_path: str,
    log_dir: Optional[str] = None,
    artifact_dir: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Parse JUnit XML file to extract failed test cases, including tracebacks and logs.
    
    :param junit_path: Path to the JUnit XML file
    :param log_dir: Optional directory containing structured logs
    :param artifact_dir: Optional directory for additional artifacts
    :return: List of failure dictionaries
    """
    tree = ET.parse(junit_path)
    root = tree.getroot()
    
    failures = []
    ns = {'junit': 'http://www.nunit.org/nunit-2.5/'}  # Adjust if needed for pytest JUnit
    
    for testsuite in root.findall('.//testsuite', ns) or root.findall('.//testsuite'):
        for testcase in testsuite.findall('testcase'):
            failure_elem = testcase.find('failure')
            error_elem = testcase.find('error')
            system_out = testcase.find('system-out')
            system_err = testcase.find('system-err')
            
            if failure_elem is not None or error_elem is not None:
                failure = failure_elem if failure_elem is not None else error_elem
                test_name = testcase.get('name', 'unknown')
                classname = testcase.get('classname', 'unknown')
                message = failure.get('message', '')
                traceback = (failure.text or '') + '\n'
                
                # Append system-out/err if present
                if system_out is not None:
                    traceback += system_out.text or ''
                if system_err is not None:
                    traceback += system_err.text or ''
                
                # Extract logs if log_dir provided
                log_content = ''
                if log_dir:
                    log_pattern = re.escape(classname.replace('.', '_')) + '.*' + re.escape(test_name) + '.*\\.log'
                    for log_file in Path(log_dir).glob('*.log'):
                        if re.match(log_pattern, log_file.name):
                            log_content += log_file.read_text(encoding='utf-8') + '\n'
                
                full_trace = traceback + log_content
                
                # Anonymize
                anonymized_trace = anonymize(full_trace)
                
                failures.append({
                    'test_name': test_name,
                    'classname': classname,
                    'message': message,
                    'traceback': anonymized_trace.strip()
                })
    
    return failures


def anonymize(text: str) -> str:
    """
    Anonymize sensitive information in traces and logs.
    
    :param text: Text to anonymize
    :return: Anonymized text
    """
    # Replace absolute paths
    text = re.sub(r'(/workspaces/[^\s\n]+)', r'/workspace/project', text)
    text = re.sub(r'(/home/[^\s\n]+)', r'/home/user', text)
    
    # Replace IP addresses
    text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', 'x.x.x.x', text)
    
    # Remove API keys, secrets (basic pattern matching)
    text = re.sub(r'(?i)(api[_-]?key|token|secret)[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', r'\1: [REDACTED]', text)
    
    # Remove commit hashes or specific IDs if needed
    text = re.sub(r'[a-f0-9]{40}', '[COMMIT_HASH]', text)
    
    return text


def build_payload(
    failures: List[Dict[str, str]],
    commit_sha: str = '',
    branch: str = '',
    pr_number: Optional[int] = None
) -> Dict:
    """
    Build JSON payload for AI analyzer.
    
    :param failures: List of failure dicts
    :param commit_sha: Current commit SHA
    :param branch: Branch name
    :param pr_number: PR number if applicable
    :return: Payload dictionary
    """
    payload = {
        'project': 'pure3270',
        'commit_sha': commit_sha,
        'branch': branch,
        'pr_number': pr_number,
        'num_failures': len(failures),
        'failures': failures
    }
    return payload


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python failure_parser.py <junit.xml> [log_dir]")
        sys.exit(1)
    
    junit_path = sys.argv[1]
    log_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    failures = parse_junit_failures(junit_path, log_dir)
    payload = build_payload(failures)
    
    print(json.dumps(payload, indent=2))