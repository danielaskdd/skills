#!/usr/bin/env python3
"""
ABOUTME: Generates HTML audit reports from audit manifest
ABOUTME: Includes statistics, issue details, and source tracing
"""

import argparse
import html
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from jinja2 import Environment
except ImportError:
    Environment = None


# Default HTML template (used if no custom template provided)
DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Audit Report</title>
    <style>
        :root {
            --primary: #2563eb;
            --danger: #dc2626;
            --warning: #d97706;
            --success: #16a34a;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-600: #4b5563;
            --gray-800: #1f2937;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--gray-800);
            background: var(--gray-50);
            padding: 2rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }

        h1 {
            color: var(--gray-800);
            margin-bottom: 0.5rem;
        }

        .meta {
            color: var(--gray-600);
            font-size: 0.875rem;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .stat-card h3 {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--gray-600);
            margin-bottom: 0.5rem;
        }

        .stat-card .value {
            font-size: 2rem;
            font-weight: bold;
        }

        .stat-card.danger .value { color: var(--danger); }
        .stat-card.warning .value { color: var(--warning); }
        .stat-card.success .value { color: var(--success); }

        .section {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }

        .section h2 {
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--gray-200);
        }

        .issue {
            border: 1px solid var(--gray-200);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        .issue.high {
            border-left: 4px solid var(--danger);
        }

        .issue.medium {
            border-left: 4px solid var(--warning);
        }

        .issue.low {
            border-left: 4px solid var(--success);
        }

        .issue-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .issue-title {
            font-weight: 600;
            color: var(--gray-800);
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .badge.high { background: #fee2e2; color: var(--danger); }
        .badge.medium { background: #fef3c7; color: var(--warning); }
        .badge.low { background: #dcfce7; color: var(--success); }
        .badge.category { background: var(--gray-100); color: var(--gray-600); }

        .issue-content {
            margin-bottom: 1rem;
        }

        .issue-content label {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--gray-600);
            display: block;
            margin-bottom: 0.25rem;
        }

        .issue-content p {
            margin-bottom: 1rem;
        }

        .source-text {
            background: var(--gray-100);
            padding: 1rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.875rem;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .suggestion {
            background: #ecfdf5;
            padding: 1rem;
            border-radius: 4px;
            border: 1px solid #a7f3d0;
        }

        .distribution-chart {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .chart-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .chart-bar {
            width: 100px;
            height: 20px;
            background: var(--gray-200);
            border-radius: 4px;
            overflow: hidden;
        }

        .chart-fill {
            height: 100%;
            background: var(--primary);
        }

        footer {
            text-align: center;
            color: var(--gray-600);
            font-size: 0.875rem;
            padding: 2rem;
        }

        @media print {
            body { padding: 0; background: white; }
            .container { max-width: none; }
            .section { box-shadow: none; border: 1px solid var(--gray-200); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Document Audit Report</h1>
            <p class="meta">Generated: {{ generated_at }} | Total Blocks: {{ total_blocks }}</p>
        </header>

        <div class="stats">
            <div class="stat-card {{ 'danger' if violation_count > 0 else 'success' }}">
                <h3>Total Issues</h3>
                <div class="value">{{ violation_count }}</div>
            </div>
            <div class="stat-card">
                <h3>Blocks Audited</h3>
                <div class="value">{{ total_blocks }}</div>
            </div>
            <div class="stat-card danger">
                <h3>High Severity</h3>
                <div class="value">{{ severity_counts.get('high', 0) }}</div>
            </div>
            <div class="stat-card warning">
                <h3>Medium Severity</h3>
                <div class="value">{{ severity_counts.get('medium', 0) }}</div>
            </div>
        </div>

        <div class="section">
            <h2>Issue Distribution by Category</h2>
            <div class="distribution-chart">
                {% for category, count in category_counts.items() %}
                <div class="chart-item">
                    <span class="badge category">{{ category }}</span>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: {{ (count / max_category_count * 100) if max_category_count > 0 else 0 }}%"></div>
                    </div>
                    <span>{{ count }}</span>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2>Issues Found ({{ violation_count }})</h2>
            {% if violations %}
                {% for v in violations %}
                <div class="issue {{ v.severity }}">
                    <div class="issue-header">
                        <div>
                            <span class="issue-title">{{ v.heading }}</span>
                            <span class="badge category">{{ v.issue_type }}</span>
                        </div>
                        <span class="badge {{ v.severity }}">{{ v.severity|upper }}</span>
                    </div>
                    <div class="issue-content">
                        <label>Source Text</label>
                        <div class="source-text">{{ v.content[:500] }}{% if v.content|length > 500 %}...{% endif %}</div>
                    </div>
                    <div class="issue-content">
                        <label>Rule Violated</label>
                        <p><strong>{{ v.rule_id }}</strong>: {{ v.violation_reason }}</p>
                    </div>
                    {% if v.suggestion %}
                    <div class="issue-content">
                        <label>Suggested Correction</label>
                        <div class="suggestion">{{ v.suggestion }}</div>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <p style="color: var(--success); font-weight: 500;">No issues found. Document passed all audit rules.</p>
            {% endif %}
        </div>

        <footer>
            <p>Generated by Document Audit Skill v1.0.0</p>
        </footer>
    </div>
</body>
</html>"""


def load_manifest(file_path: str) -> list:
    """
    Load audit results from manifest JSONL file.

    Args:
        file_path: Path to manifest file

    Returns:
        List of audit result dictionaries
    """
    results = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def determine_severity(entry: dict) -> str:
    """
    Determine severity level for an entry.

    Args:
        entry: Audit result entry

    Returns:
        Severity string: 'high', 'medium', or 'low'
    """
    # Check if severity is explicitly set
    if 'severity' in entry:
        return entry['severity']

    # Check violations list
    violations = entry.get('violations', [])
    if violations:
        # Get highest severity from all violations
        for v in violations:
            if v.get('issue_type') in ['semantic_risk', 'logic', 'compliance']:
                return 'high'
        for v in violations:
            if v.get('issue_type') in ['clarity', 'grammar']:
                return 'medium'
        return 'low'

    # Default based on issue_type
    issue_type = entry.get('issue_type', 'other')
    if issue_type in ['semantic_risk', 'logic', 'compliance']:
        return 'high'
    elif issue_type in ['clarity', 'grammar']:
        return 'medium'
    else:
        return 'low'


def generate_report_data(manifest: list) -> dict:
    """
    Generate report data from manifest.

    Args:
        manifest: List of audit result entries

    Returns:
        Dictionary with report data
    """
    violations = []
    category_counts = Counter()
    severity_counts = Counter()

    for entry in manifest:
        if not entry.get('is_violation', False):
            continue

        # Handle multiple violations per block
        entry_violations = entry.get('violations', [])
        if entry_violations:
            for v in entry_violations:
                issue_type = v.get('issue_type', 'other')
                severity = 'high' if issue_type in ['semantic_risk', 'logic', 'compliance'] else 'medium'

                violations.append({
                    'uuid': entry.get('uuid', ''),
                    'heading': entry.get('p_heading', ''),
                    'content': entry.get('p_content', ''),
                    'issue_type': issue_type,
                    'severity': severity,
                    'rule_id': v.get('rule_id', ''),
                    'violation_reason': v.get('violation_reason', ''),
                    'suggestion': v.get('suggestion', '')
                })

                category_counts[issue_type] += 1
                severity_counts[severity] += 1
        else:
            # Single violation (backward compatibility)
            issue_type = entry.get('issue_type', 'other')
            severity = determine_severity(entry)

            violations.append({
                'uuid': entry.get('uuid', ''),
                'heading': entry.get('p_heading', ''),
                'content': entry.get('p_content', ''),
                'issue_type': issue_type,
                'severity': severity,
                'rule_id': entry.get('rule_id', ''),
                'violation_reason': entry.get('violation_reason', ''),
                'suggestion': entry.get('suggestion', '')
            })

            category_counts[issue_type] += 1
            severity_counts[severity] += 1

    # Sort violations by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    violations.sort(key=lambda x: severity_order.get(x['severity'], 3))

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_blocks': len(manifest),
        'violation_count': len(violations),
        'violations': violations,
        'category_counts': dict(category_counts),
        'severity_counts': dict(severity_counts),
        'max_category_count': max(category_counts.values()) if category_counts else 0
    }


def render_report(data: dict, template_path: Optional[str] = None, trusted_html: bool = False) -> str:
    """
    Render HTML report from data.

    Args:
        data: Report data dictionary
        template_path: Optional path to custom template

    Returns:
        Rendered HTML string
    """
    if Environment is None:
        # Fallback without Jinja2
        return render_report_simple(data, trusted_html=trusted_html)

    # Load template
    if template_path and Path(template_path).exists():
        template_str = Path(template_path).read_text(encoding='utf-8')
    else:
        template_str = DEFAULT_TEMPLATE

    env = Environment(autoescape=not trusted_html)
    template = env.from_string(template_str)
    return template.render(**data)


def render_report_simple(data: dict, trusted_html: bool = False) -> str:
    """
    Render a simple HTML report without Jinja2.

    Args:
        data: Report data dictionary

    Returns:
        Rendered HTML string
    """
    def maybe_escape(value: str) -> str:
        if trusted_html:
            return value
        return html.escape(value, quote=True)

    violations_html = ""
    for v in data['violations']:
        heading = maybe_escape(str(v['heading']))
        issue_type = maybe_escape(str(v['issue_type']))
        severity = maybe_escape(str(v['severity']))
        violation_reason = maybe_escape(str(v['violation_reason']))
        content = maybe_escape(str(v['content'])[:200])
        suggestion = maybe_escape(str(v['suggestion']))
        violations_html += f"""
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-left: 4px solid {'#dc2626' if v['severity'] == 'high' else '#d97706'};">
            <h4>{heading}</h4>
            <p><strong>Type:</strong> {issue_type} | <strong>Severity:</strong> {severity}</p>
            <p><strong>Reason:</strong> {violation_reason}</p>
            <p><strong>Source:</strong> {content}...</p>
            {f"<p><strong>Suggestion:</strong> {suggestion}</p>" if v['suggestion'] else ""}
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Document Audit Report</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; }}
        h1 {{ color: #333; }}
        .stat {{ display: inline-block; margin: 10px; padding: 10px 20px; background: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>Document Audit Report</h1>
    <p>Generated: {data['generated_at']}</p>
    <div>
        <div class="stat">Total Blocks: {data['total_blocks']}</div>
        <div class="stat">Issues Found: {data['violation_count']}</div>
        <div class="stat">High Severity: {data['severity_counts'].get('high', 0)}</div>
    </div>
    <h2>Issues</h2>
    {violations_html if violations_html else "<p>No issues found.</p>"}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML audit report from manifest"
    )
    parser.add_argument(
        "manifest",
        type=str,
        help="Path to audit manifest JSONL file"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="audit_report.html",
        help="Output HTML file path (default: audit_report.html)"
    )
    parser.add_argument(
        "--template", "-t",
        type=str,
        help="Path to custom Jinja2 HTML template"
    )
    parser.add_argument(
        "--trusted-html",
        action="store_true",
        help="Render report without HTML escaping (only for trusted inputs)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output report data as JSON"
    )

    args = parser.parse_args()

    # Validate input
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    # Load and process manifest
    print(f"Loading manifest: {args.manifest}")
    manifest = load_manifest(args.manifest)
    print(f"Loaded {len(manifest)} entries")

    # Generate report data
    data = generate_report_data(manifest)
    print(f"Found {data['violation_count']} issues")

    # Render HTML
    html = render_report(data, args.template, trusted_html=args.trusted_html)

    # Save HTML
    output_path = Path(args.output)
    output_path.write_text(html, encoding='utf-8')
    print(f"HTML report saved to: {output_path}")

    # Optionally save JSON
    if args.json:
        json_path = output_path.with_suffix('.json')
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"JSON data saved to: {json_path}")

    # Summary
    print("\n--- Summary ---")
    print(f"Total blocks: {data['total_blocks']}")
    print(f"Issues found: {data['violation_count']}")
    print(f"By severity: {dict(data['severity_counts'])}")
    print(f"By category: {dict(data['category_counts'])}")


if __name__ == "__main__":
    main()
