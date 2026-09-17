# Frontend integration reference (not applied — no push access to the repo)

The existing `src/pages/customer/AIChatbotPage.jsx` already has a complete, working chat UI
with a `// TODO: Replace this demo response with your Llama/FastAPI API call later.` comment
marking exactly where to wire this up — verified by reading the file directly (see
`../docs/AI_CONTEXT.md` section A). No new UI needs to be built; only `sendMessage()`'s
`window.setTimeout(() => { ... getLocalReply(trimmed) ... })` block needs to call the real
endpoint.

This file shows the minimal diff. It is a reference, not applied to the cloned repo, because
this session has no push/merge credentials for `ultimate-final-frontend`.

## New file: `src/features/chatbot/api/chatbotApi.js`

```js
import axiosInstance from '../../../shared/lib/axiosInstance';

export const chatbotApi = {
  sendMessage: async ({ message, conversationId }) => {
    const { data } = await axiosInstance.post('/chat', {
      message,
      conversation_id: conversationId || null,
    });
    return data; // { conversation_id, message, language, intent, category, problem, priority, actions, redirect }
  },
};

export default chatbotApi;
```

Notes on why this reuses the existing `axiosInstance`:
- Same `baseURL` pattern (`VITE_API_URL`) — except the chatbot service runs on a different
  port than the Node backend, so in practice this needs its OWN axios instance pointed at
  `VITE_CHATBOT_API_URL` (e.g. `http://localhost:8000/api`), still with `withCredentials: true`
  so the browser forwards the same `accessToken` cookie the chatbot service relays to Node's
  `/api/auth/me` (see `../app/auth/session.py`). A one-line variant of
  `shared/lib/axiosInstance.js` with a different `baseURL` env var is the smallest change that
  keeps this consistent with how the rest of the app already talks to its backend.

## Changed: `src/pages/customer/AIChatbotPage.jsx`

```diff
-import { useAuth } from '../../features/auth/hooks/useAuth';
+import { useAuth } from '../../features/auth/hooks/useAuth';
+import chatbotApi from '../../features/chatbot/api/chatbotApi';
```

```diff
   const [messages, setMessages] = useState(initialMessages);
   const [input, setInput] = useState('');
   const [isTyping, setIsTyping] = useState(false);
+  const [conversationId, setConversationId] = useState(null);
```

```diff
-    // TODO: Replace this demo response with your Llama/FastAPI API call later.
-    window.setTimeout(() => {
-      const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
-      setMessages((current) => [
-        ...current,
-        { id: createId(), role: 'assistant', text: getLocalReply(trimmed), time: replyTime },
-      ]);
-      setIsTyping(false);
-    }, 650);
+    chatbotApi
+      .sendMessage({ message: trimmed, conversationId })
+      .then((data) => {
+        setConversationId(data.conversation_id);
+        const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
+        setMessages((current) => [
+          ...current,
+          { id: createId(), role: 'assistant', text: data.message, time: replyTime },
+        ]);
+        if (data.redirect) {
+          // Surface as a "view services"-style action rather than an
+          // automatic navigate — never redirect the user without them
+          // choosing to, per the master prompt's "confirmation required"
+          // rule for anything that changes what they're looking at.
+        }
+      })
+      .catch(() => {
+        setMessages((current) => [
+          ...current,
+          {
+            id: createId(),
+            role: 'assistant',
+            text: "Sorry, I couldn't reach the assistant just now. Please try again.",
+            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
+          },
+        ]);
+      })
+      .finally(() => setIsTyping(false));
```

That's the entire integration — the rest of the existing UI (message list, suggested prompts,
typing indicator, scroll handling) works unchanged. `getLocalReply()` and the "Frontend demo" /
"Llama ready" badges in the sidebar can be removed once this is wired up for real.

## Also required: a worker-facing chat entry point

The master spec (Section 6) requires the chatbot to help workers too, but today
`AIChatbotPage.jsx` is customer-only (`if (!isAuthenticated || !isCustomer) return null;`,
router-mounted only under `/customer/ai-chat`). The backend `/api/chat` endpoint already
supports any authenticated role — the Python service reads `user.role` from Node's `/auth/me`
and branches on it (see `app/services/orchestrator.py`). The missing piece is purely a
frontend route: mount the same page (with its customer-only guard changed to allow
`professional`) at a path under `WorkerLayout`, e.g. `/worker/ai-chat`, in
`src/app/router/AppRoutes.jsx`. Not built here since it touches the live frontend router file
this session cannot push to — flagging it explicitly as a remaining frontend task rather than
silently leaving it undiscovered.
