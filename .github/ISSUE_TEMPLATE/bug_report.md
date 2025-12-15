name: Bug report
about: Something isn’t working
title: "[Bug] "
labels: bug
body:
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us what you expected to happen.
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Steps to reproduce
      description: Minimal commands or config to trigger the issue.
      placeholder: |
        1. ...
        2. ...
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Logs / stacktrace
      description: Add relevant snippets (redact secrets).
  - type: input
    id: os
    attributes:
      label: OS + Shell
      placeholder: "Windows 11 + PowerShell 7 / macOS 14 + zsh"
  - type: input
    id: python
    attributes:
      label: Python version
      placeholder: "3.11.9"
  - type: input
    id: ollama
    attributes:
      label: Ollama version
      placeholder: "0.3.x"
