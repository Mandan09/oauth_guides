# Tests that passed

All of these were run through the chat UI, the way a developer would use it.

## Guides generated live

| App | Prompt | Result |
|---|---|---|
| Google Drive | "How do I set up OAuth for Google Drive so users can connect their accounts to my AI agent?" | ✅ Rated hard; separated `drive.file` from restricted scopes that need a CASA assessment |
| Gmail | "My AI assistant needs to read emails and send replies using Gmail. What OAuth permissions do I need?" | ✅ Rated hard; Google verification plus annual CASA for restricted Gmail scopes |
| Dropbox | "Connect Dropbox so my assistant can upload, download and search files" | ✅ Rated moderate; all three scopes confirmed against the docs |
| GitHub | "AI coding assistant that needs repositories and pull requests" | ✅ Guide generated |
| Microsoft Outlook | "How can users connect their Outlook accounts to my SaaS app?" | ✅ Rated moderate; Publisher Verification needed for external tenants |
| Zoho CRM | "Investigate the official developer portal and tell me what I need" | ✅ Rated easy; all sources from zoho.com |
| Keka (unfamiliar HR platform) | "Here is its website: keka.com. Does it support OAuth?" | ✅ Rated moderate; sandbox approval plus marketplace review |
| Calendly (on the live Render site) | "My agent schedules meetings and checks availability" | ✅ Rated easy; PKCE required |

## Library guides and recommendations

| Test | Result |
|---|---|
| HubSpot: customer records and deals | ✅ Opened from the library instantly, then mapped the use case to `crm.objects.contacts.read`, `crm.objects.deals.write` and related scopes |
| Vague project-management request | ✅ Recommended Asana, with Linear and Jira as alternatives |
| "Jira guide" typed while another guide was open | ✅ Opened the Jira guide |

## Tricky inputs

| Test | Result |
|---|---|
| `https://example.com` | ✅ Recognised as a placeholder domain with no OAuth; stopped early instead of inventing a guide |
| "An API documentation page" with no link | ✅ Asked for the name or URL |
| "The provider hasn't approved my app", no provider named | ✅ Asked which provider |
| "Users see an unverified app warning" | ✅ Answered generally (Google verification, Microsoft publisher verification) |
| Follow-up question about the open Asana guide | ✅ Answered from the guide, with links to Asana's docs |
| Off-topic question | ✅ Politely redirected |

## Checklist

| Check | Result |
|---|---|
| Identifies the right app or provider | ✅ |
| Finds the official developer documentation | ✅ |
| Identifies the authentication method | ✅ |
| Lists the scopes and permissions needed | ✅ |
| Covers developer account and registration steps | ✅ |
| Gives step-by-step instructions | ✅ |
| Separates your effort from the provider's approval wait | ✅ |
| Covers verification and publishing requirements | ✅ |
| Marks which steps an agent can do and which need you | ✅ |
| Cites sources for important claims | ✅ |
| Marks assumptions and unverified information | ✅ |
| Produces a guide you can keep and share | ✅ |

Unit tests for the evidence checks: `pytest` (4 passing).
