---
type: checklist
created: 2026-02-26T01:30:39+09:00
domain: security
confidence: 0.6355
tags: [ssrf, security, review-checklist, owasp]
last_referenced: 2026-02-27T18:31:12+09:00
---
# SSRF Review Checklist

## Check
- [ ] User-supplied URLs validated against allowlist
- [ ] Internal IP ranges blocked (10.x, 172.16-31.x, 192.168.x)
- [ ] DNS rebinding protection
- [ ] Redirect following disabled or limited
- [ ] Response content not reflected to user