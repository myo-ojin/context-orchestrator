name: Feature request
about: Suggest an idea or improvement
title: "[Feature] "
labels: enhancement
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem to solve
      description: What user pain does this feature address?
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
      description: How should it work? CLI/API/Config?
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
  - type: textarea
    id: context
    attributes:
      label: Additional context
