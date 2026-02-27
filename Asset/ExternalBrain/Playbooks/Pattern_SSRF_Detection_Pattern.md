---
type: pattern
created: 2026-02-26T00:46:31+09:00
domain: security
confidence: 0.7343
tags: [ssrf, security, owasp, url-validation]
last_referenced: 2026-02-27T18:31:49+09:00
---
# SSRF Detection Pattern\n\n## Symptoms\n- Server makes unexpected outbound requests\n- Internal IPs in user-supplied URLs\n\n## Prevention\n- Validate/sanitize URL inputs\n- Block internal IP ranges\n- Use allowlists for external domains