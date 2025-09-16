# Security Policy

Friday prioritizes safety and security. Please read carefully before working with Ops or sensitive modules.

---

## Reporting Vulnerabilities

- Please report vulnerabilities privately (set up repo security contact/email).  
- Do not disclose publicly until fixed.

---

## Secret Handling

- No `.env` files allowed.  
- All secrets/keys must be stored in volatile encrypted memory.  
- Never commit API keys, tokens, or secrets.

---

## Ops Module Scope

- Ops module is **sandboxed** by default.  
- Tools: nmap, scapy, ZAP, traffic shaping.  
- All scans limited to approved targets in `security/targets.yaml`.  
- Behavioral obfuscation allowed, but traffic must mimic human-like patterns.  
- High-risk ops require explicit human approval.

---

## Sandboxing & Policies

- All new code passes dev → sandbox → adversarial test → (optional) human → staging → prod pipeline.  
- Default policy: deny-by-default, allowlist enforced.

---

Stay safe, build responsibly.
