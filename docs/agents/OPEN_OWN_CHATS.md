# Open the two agents in your own chat screens

The Auditor and Continuation roles are playbooks. Cursor only gives you a
real chat screen when **you** start a Cloud Agent from your account.

Do not use `bc-…` IDs pasted in another chat. Those are internal run IDs
and will not open as your chats.

## 1. Open the Cloud Agents home

In a browser, while logged in as the same Cursor account that owns this
repo:

https://cursor.com/agents

Or in Cursor Desktop: open the agent input and set the dropdown to **Cloud**.

## 2. Start the Auditor chat

1. Click **New Agent**.
2. Repository: `royalindustry94-crypto/Content-orchestrator`.
3. Name it `ChatGPT Independent Auditor` if the UI asks for a name.
4. Paste the **entire** Auditor prompt from `docs/agents/LAUNCH_PROMPTS.md`
   (section 1) as the first message.
5. Send. That tab is now the Auditor screen. Bookmark it.

## 3. Start the Continuation chat

Repeat in a **second** New Agent. Name it `Build Continuation Agent`.
Paste the Continuation prompt (section 2) as the first message.

That tab is the dormant builder. Bookmark it.

## 4. Keep the roles apart

| You want to… | Use this screen |
|---|---|
| Audit ChatGPT / Codex / a PR or SHA | Auditor chat only |
| Hand over when ChatGPT is unavailable | Continuation chat only — first line `TAKEOVER` |

Do not send `TAKEOVER` to the Auditor. Do not send audit requests to the
Continuation agent.

## If a chat disappears later

Create a new Cloud Agent with the same prompt. The playbooks live in the
repo; the chat screen is just the conversation.
