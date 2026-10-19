# Integrations

## Implemented discovery (public GET)

| Provider | Config keys | Apply |
|----------|-------------|-------|
| Greenhouse | `board_token` | Hosted form / FORM_ASSISTED |
| Lever | `site`, `region` (`us`\|`eu`) | Hosted apply URL |
| Ashby | `board_name` | Hosted `applyUrl` |
| SmartRecruiters | `company_identifier` | Careers apply URL |
| RSS/Atom | `feed_url` | Link from feed |
| Manual | pasted payload | As provided |

Discovery is **per company board**, not a global job search across all employers.

## Unsupported Czech portals

| Portal | Reason | Fallback |
|--------|--------|----------|
| Jobs.cz / Práce.cz | Employer/Teamio APIs, not public candidate search | Manual import, email alerts |
| StartupJobs | Company Bearer API for own offers only | Manual import |
| Webtrh | No verified public candidate job API/RSS | Manual import |

## LLM

OpenAI-compatible `/chat/completions` and `/embeddings`. Without `LLM_API_KEY`, generation uses a deterministic template fallback; vector retrieval is skipped.

## Email

Email.cz / Seznam IMAP+SMTP. Passwords encrypted with Fernet (`SECRET_ENCRYPTION_KEY`). Never exposed to the frontend bundle.
