import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# Prompt template for regression analysis
PROMPT_TEMPLATE = """
You are an expert Python developer and CI/CD specialist. Analyze the following test failures from a Python project (Pure3270, a 3270 emulator).

Context:
- Project: Pure Python 3270 emulator
- Commit: {commit_sha}
- Branch: {branch}
- PR: {pr_number}

Failures ({num_failures}):
{failures}

Task: Perform regression analysis.
- Identify patterns or root causes (e.g., recent code changes, dependencies, env issues).
- Suggest fixes or debugging steps.
- Check if failures are flaky, regression, or environmental.
- Prioritize by impact.

Respond in JSON format only:
{{
  "summary": "Brief overview of failures",
  "root_causes": ["Cause 1", "Cause 2"],
  "patterns": ["Pattern 1", "Pattern 2"],
  "recommendations": ["Fix 1", "Fix 2"],
  "is_regression": true/false,
  "priority": "high/medium/low",
  "next_steps": ["Step 1", "Step 2"]
}}

Be concise, actionable, and code-focused.
"""


def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    """
    Generate Markdown report from AI analysis JSON.
    
    :param analysis: JSON response from OpenAI
    :return: Markdown report content
    """
    md = f"# Regression Analysis Report\n\n"
    md += f"**Project:** Pure3270\n"
    md += f"**Summary:** {analysis.get('summary', 'N/A')}\n\n"
    
    md += "## Root Causes\n"
    for cause in analysis.get('root_causes', []):
        md += f"- {cause}\n"
    
    md += "\n## Patterns\n"
    for pattern in analysis.get('patterns', []):
        md += f"- {pattern}\n"
    
    md += "\n## Recommendations\n"
    for rec in analysis.get('recommendations', []):
        md += f"- {rec}\n"
    
    md += f"\n## Assessment\n"
    md += f"- Is Regression: {analysis.get('is_regression', False)}\n"
    md += f"- Priority: {analysis.get('priority', 'medium')}\n\n"
    
    md += "## Next Steps\n"
    for step in analysis.get('next_steps', []):
        md += f"- {step}\n"
    
    return md


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_failures(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Call OpenAI API to analyze failures.
    
    :param payload: Payload from failure_parser
    :param api_key: OpenAI API key
    :return: Parsed JSON analysis
    """
    if os.getenv('MOCK_ANALYSIS', 'false').lower() == 'true':
        # Mock response for local testing
        return {
            "summary": "Mock analysis: Tests passed, no failures detected.",
            "root_causes": ["None"],
            "patterns": ["No failures"],
            "recommendations": ["No action needed"],
            "is_regression": False,
            "priority": "low",
            "next_steps": ["Review if needed"]
        }
    
    client = OpenAI(api_key=api_key)
    
    prompt = PROMPT_TEMPLATE.format(
        commit_sha=payload.get('commit_sha', ''),
        branch=payload.get('branch', ''),
        pr_number=payload.get('pr_number', 'N/A'),
        num_failures=payload.get('num_failures', 0),
        failures=json.dumps(payload.get('failures', []), indent=2)
    )
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that responds only in JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from OpenAI")
    
    # Parse JSON from content
    try:
        analysis = json.loads(content)
    except json.JSONDecodeError as e:
        # Fallback: try to extract JSON
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            analysis = json.loads(content[json_start:json_end])
        else:
            raise ValueError(f"Invalid JSON response: {e}")
    
    return analysis

def run_analysis(
    payload_path: str,
    output_dir: str,
    api_key: Optional[str] = None
) -> Path:
    """
    Main entry point: Load payload, analyze, generate report.
    
    :param payload_path: Path to JSON payload from failure_parser
    :param output_dir: Directory to save report
    :param api_key: OpenAI API key (from env if None)
    :return: Path to generated report
    """
    if api_key is None:
        api_key = os.getenv('OPENAI_API_KEY')
    
    if os.getenv('MOCK_ANALYSIS', 'false').lower() == 'true':
        api_key = "mock_key"
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    with open(payload_path, 'r') as f:
        payload = json.load(f)
    
    analysis = analyze_failures(payload, api_key)
    
    report_path = Path(output_dir) / "regression_analysis.md"
    report_content = generate_markdown_report(analysis)
    
    report_path.write_text(report_content, encoding='utf-8')
    
    return report_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ai_analyzer.py <payload.json> <output_dir> [api_key]")
        sys.exit(1)
    
    payload_path = sys.argv[1]
    output_dir = sys.argv[2]
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        report = run_analysis(payload_path, output_dir, api_key)
        print(f"Report generated: {report}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)