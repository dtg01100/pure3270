const fs = require('fs');

function usage() {
  console.error('Usage: node simulate_copilot_label_check.js <payload.json> <event_name>');
  process.exit(2);
}

if (process.argv.length < 4) usage();
const payloadPath = process.argv[2];
const eventName = process.argv[3];

let payload;
try {
  payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
} catch (e) {
  console.error('Failed to read/parse payload:', e.message);
  process.exit(1);
}

const issue = payload.issue || (payload.comment && payload.comment.issue);

function labelsOf(issue) {
  if (!issue) return [];
  if (!issue.labels) return [];
  return issue.labels.map(l => (typeof l === 'string' ? l : l.name));
}

function evaluate(issueObj, event) {
  if (!issueObj) return { should_run: false, reason: 'no issue found in payload' };
  const labels = labelsOf(issueObj);
  const hasRegression = labels.includes('regression');
  const hasPythonVersion = labels.includes('python-version');
  const hasCopilotLabel = labels.includes('copilot-assist') || labels.includes('needs-ai-analysis');
  const should_run = hasRegression && hasPythonVersion && (hasCopilotLabel || event === 'issues');
  return { should_run, labels, hasRegression, hasPythonVersion, hasCopilotLabel, event };
}

const result = evaluate(issue, eventName);
console.log(JSON.stringify(result, null, 2));
