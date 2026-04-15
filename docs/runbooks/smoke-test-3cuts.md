# 3-Cut Smoke Test Guide

> Verification guide for: topic-aware session, claude_runtime worker queue, session stickiness

---

## Prerequisites

### 1. Start the API server

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack

# Set required env vars
export AUTORESEARCH_TELEGRAM_BOT_TOKEN="your-bot-token"
export AUTORESEARCH_TELEGRAM_OWNER_UIDS="your-telegram-user-id"
export AUTORESEARCH_TELEGRAM_SECRET_TOKEN="your-webhook-secret"

# Start API
make start
# or: python -m autoresearch.api.main
```

### 2. Register webhook

```bash
# Replace with your actual values
BOT_TOKEN="your-bot-token"
SECRET="your-webhook-secret"
WEBHOOK_URL="https://your-server/api/v1/gateway/telegram/webhook"

curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}&secret_token=${SECRET}"
```

### 3. Start a Mac worker (optional but needed for full chain)

```bash
export AUTORESEARCH_WORKER_ID="smoke-test-worker-01"
export AUTORESEARCH_API_BASE_URL="http://localhost:8000"
python -m autoresearch.workers.mac.daemon
```

---

## Test 1: Private Chat — Basic Chain

**Goal:** Verify webhook -> session -> enqueue -> (worker claim -> execute) -> notify

### Steps

1. Open Telegram, find your bot in private chat
2. Send: `你好，测试私聊`

### What to check

```bash
# Check the queue — should see a CLAUDE_RUNTIME task
curl -s http://localhost:8000/api/v1/worker-runs | python3 -m json.tool | grep -A5 "claude_runtime"

# Check session was created with correct key
curl -s http://localhost:8000/api/v1/openclaw/sessions | python3 -m json.tool | grep -A3 "session_key"
# Expected: "session_key": "telegram:personal:user:<your_uid>"

# Check chat_context has no thread fields
curl -s http://localhost:8000/api/v1/openclaw/sessions | python3 -m json.tool | grep -A5 "chat_context"
# Expected: message_thread_id: null, is_topic_message: false
```

### Expected behavior

- Bot replies "已接收，已排队：tg_..." 
- If worker is running: task claimed, executed, result sent back to private chat
- If no worker: task stays QUEUED, visible in queue listing

### Pass criteria

- [ ] Webhook returns `accepted: true, metadata.routed_to: "worker_queue"`
- [ ] Session key is `telegram:personal:user:<uid>`
- [ ] Queue item has `task_type: "claude_runtime"`
- [ ] Bot reply arrives in private chat (with or without worker)

---

## Test 2: Private Chat — Consecutive Messages

**Goal:** Verify session continuity and sticky binding

### Steps

1. In the same private chat, send: `记住：我的偏好是中文回复`
2. Wait for response
3. Send: `我刚才说了什么？`

### What to check

```bash
# Check session events — should have 3+ user messages in the same session
curl -s http://localhost:8000/api/v1/openclaw/sessions/<session_id> | python3 -m json.tool | grep '"role"' 

# Check sticky record exists for this session_key
curl -s http://localhost:8000/api/v1/worker-runs | python3 -m json.tool | grep "preferred_worker_id"
```

### Pass criteria

- [ ] All messages go to the same session (same session_id)
- [ ] Same session_key across messages
- [ ] If worker ran: sticky record has worker_id bound

---

## Test 3: Create Test Supergroup with Topics

**Goal:** Set up the group environment for topic testing

### Steps

1. In Telegram, create a new group
2. Convert it to **supergroup** (usually automatic for groups > 200 members, or use @BotFather's `/setjoingroups`)
3. Go to group settings -> **Turn on Topics**
4. Add your bot to the group
5. Make sure bot has permission to send messages

### Create two test topics

- Topic A: name it "测试话题A"
- Topic B: name it "测试话题B"

---

## Test 4: Same Topic — Consecutive Messages

**Goal:** Verify topic-scoped session key and reply-to-thread

### Steps

1. Go to **Topic A**
2. Send: `这是话题A的第一条消息`
3. Wait for bot reply
4. Send: `这是话题A的第二条消息`

### What to check

```bash
# Find the session for this topic
curl -s http://localhost:8000/api/v1/openclaw/sessions | python3 -m json.tool | grep -B2 -A5 "topic:"

# Expected session_key: "telegram:shared:chat:<chat_id>:topic:<thread_id>"
# Expected: chat_context.message_thread_id is NOT null
# Expected: chat_context.is_topic_message is true

# Check bot replies landed in the topic, not group main
# (check in Telegram app — replies should be inside Topic A)
```

### Pass criteria

- [ ] Session key contains `:topic:<thread_id>`
- [ ] `chat_context.message_thread_id` matches the topic's thread ID
- [ ] Bot replies appear **inside Topic A**, not in the group main feed
- [ ] Both messages share the same session (same session_id)

---

## Test 5: Different Topics — Session Isolation

**Goal:** Verify two topics in the same group do NOT share session

### Steps

1. Go to **Topic A**, send: `话题A专属信息`
2. Go to **Topic B**, send: `话题B专属信息`
3. Go to **Topic A**, send: `我刚才在话题A说了什么？`
4. Go to **Topic B**, send: `我刚才在话题B说了什么？`

### What to check

```bash
# List all sessions, should see TWO different session keys for the same chat_id
curl -s http://localhost:8000/api/v1/openclaw/sessions | python3 -m json.tool | grep "session_key"
# Expected: two entries like:
#   "telegram:shared:chat:<chat_id>:topic:<thread_A>"
#   "telegram:shared:chat:<chat_id>:topic:<thread_B>"

# Verify Topic A's session does NOT contain Topic B's messages
curl -s http://localhost:8000/api/v1/openclaw/sessions/<topic_A_session_id> | python3 -m json.tool | grep "话题B"
# Expected: NO results

# Verify Topic B's session does NOT contain Topic A's messages  
curl -s http://localhost:8000/api/v1/openclaw/sessions/<topic_B_session_id> | python3 -m json.tool | grep "话题A"
# Expected: NO results
```

### Pass criteria

- [ ] Topic A and Topic B have **different session keys**
- [ ] Topic A session only contains Topic A messages
- [ ] Topic B session only contains Topic B messages
- [ ] Bot replies land in the correct topic each time
- [ ] No cross-contamination between topics

---

## Test 6: Sticky Worker Binding

**Goal:** Verify consecutive requests from same session_key hit the same worker

### Steps

1. Make sure a worker is running
2. Send 3 messages in a row in the same topic (or private chat)
3. Check worker binding records

### What to check

```bash
# After each message, check the queue item's preferred_worker_id
curl -s http://localhost:8000/api/v1/worker-runs | python3 -m json.tool | grep -A3 "preferred_worker_id"

# After worker processes, check sticky record
# The session_records table should show the same worker_id for consecutive runs
```

### Pass criteria

- [ ] Second and third requests have `preferred_worker_id` set
- [ ] `preferred_worker_id` matches the worker that processed the first request
- [ ] If worker is healthy, same worker claims all tasks for this session

---

## Test 7: Command Regression

**Goal:** Verify /status, /reset, /mode still work correctly

### Steps

1. Private chat: send `/status`
2. Private chat: send `/reset`
3. Private chat: send `/mode shared`
4. In a topic: send `/status`
5. In a topic: send `/reset`

### Pass criteria

- [ ] `/status` returns current session info, does not crash
- [ ] `/reset` creates a new session, old one archived
- [ ] `/mode shared` switches scope (private chat only)
- [ ] `/status` in a topic shows topic-scoped session
- [ ] `/reset` in a topic creates new topic-scoped session (not a group-wide reset)

---

## Quick Diagnostic Commands

```bash
# See all queued/running/completed tasks
curl -s http://localhost:8000/api/v1/worker-runs | python3 -m json.tool

# See all sessions  
curl -s http://localhost:8000/api/v1/openclaw/sessions | python3 -m json.tool

# See registered workers
curl -s http://localhost:8000/api/v1/workers | python3 -m json.tool

# See session details (replace with actual ID)
curl -s http://localhost:8000/api/v1/openclaw/sessions/<session_id> | python3 -m json.tool

# See worker run details
curl -s http://localhost:8000/api/v1/worker-runs/<run_id> | python3 -m json.tool
```

---

## Test Results Template

| Test | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | Private chat basic chain | PASS/FAIL | |
| 2 | Private chat consecutive | PASS/FAIL | |
| 3 | Supergroup + topics setup | PASS/FAIL | |
| 4 | Same topic consecutive | PASS/FAIL | |
| 5 | Different topics isolation | PASS/FAIL | |
| 6 | Sticky worker binding | PASS/FAIL | |
| 7 | Command regression | PASS/FAIL | |
