# AI Prompt Engineering & Safety Best Practices

## Your Mission

As GitHub Copilot, you must understand and apply the principles of effective prompt engineering, AI safety, and responsible AI usage. Your goal is to help developers create prompts that are clear, safe, unbiased, and effective while following industry best practices and ethical guidelines. When generating or reviewing prompts, always consider safety, bias, security, and responsible AI usage alongside functionality.

## Introduction

Prompt engineering is the art and science of designing effective prompts for large language models (LLMs) and AI assistants like GitHub Copilot. Well-crafted prompts yield more accurate, safe, and useful outputs. This guide covers foundational principles, safety, bias mitigation, security, responsible AI usage, and practical templates/checklists for prompt engineering.

### What is Prompt Engineering?

Prompt engineering involves designing inputs (prompts) that guide AI systems to produce desired outputs. It's a critical skill for anyone working with LLMs, as the quality of the prompt directly impacts the quality, safety, and reliability of the AI's response.

## Table of Contents

1. What is Prompt Engineering?
2. Prompt Engineering Fundamentals
3. Safety & Bias Mitigation
4. Responsible AI Usage
5. Security
6. Testing & Validation
7. Documentation & Support
8. Templates & Checklists
9. References

## Prompt Engineering Fundamentals

### Clarity, Context, and Constraints

**Be Explicit:**
- State the task clearly and concisely
- Provide sufficient context for the AI to understand the requirements
- Specify the desired output format and structure
- Include any relevant constraints or limitations

**Use Constraints Effectively:**
- **Length:** Specify word count, character limit, or number of items
- **Style:** Define tone, formality level, or writing style
- **Format:** Specify output structure (JSON, markdown, bullet points, etc.)
- **Scope:** Limit the focus to specific aspects or exclude certain topics

## Prompt Patterns

**Zero-Shot Prompting:**
- Ask the AI to perform a task without providing examples

**Few-Shot Prompting:**
- Provide 2-3 examples of input-output pairs to help the AI understand the expected format and style

**Chain-of-Thought Prompting:**
- Ask the AI to show its reasoning process to help with complex problem-solving

**Role Prompting:**
- Assign a specific role or persona to the AI to set context and expectations

## Safety & Bias Mitigation

### Detecting Harmful or Biased Outputs

**Red-teaming:**
- Systematically test prompts for potential issues
- Identify edge cases and failure modes
- Simulate adversarial inputs

**Safety Checklist Items:**
- [ ] Does the output contain harmful content?
- [ ] Does the output promote bias or discrimination?
- [ ] Does the output violate privacy or security?
- [ ] Does the output contain misinformation?
- [ ] Does the output encourage dangerous behavior?

## Responsible AI Usage

### Transparency & Explainability

**Documenting Prompt Intent:**
- Clearly state the purpose and scope of prompts
- Document limitations and assumptions
- Explain expected behavior and outputs

### Data Privacy & Auditability

**Avoiding Sensitive Data:**
- Never include personal information in prompts
- Sanitize user inputs before processing
- Implement data minimization practices

## Security

### Preventing Prompt Injection

**Never Interpolate Untrusted Input:**
- Avoid directly inserting user input into prompts
- Use input validation and sanitization
- Implement proper escaping mechanisms

## Testing & Validation

### Automated Prompt Evaluation

- Define test cases and expected outputs for prompts
- Include safety checks and bias tests

### Human-in-the-Loop Review

- Include peer review and expert review for high-risk prompts
- Document decisions and feedback

## Documentation & Support

### Prompt Documentation

**Purpose and Usage:**
- Clearly state what the prompt does
- Explain when and how to use it
- Provide examples and use cases

## Templates & Checklists

### Prompt Design Checklist

**Task Definition:**
- [ ] Is the task clearly stated?
- [ ] Is the scope well-defined?
- [ ] Are the requirements specific?
- [ ] Is the expected output format specified?

## References

- Microsoft Responsible AI Resources
- OpenAI Prompt Engineering Guide
- Google AI Principles

---
applyTo: ['*']
description: "Comprehensive best practices for AI prompt engineering, safety frameworks, bias mitigation, and responsible AI usage for Copilot and LLMs."
---
