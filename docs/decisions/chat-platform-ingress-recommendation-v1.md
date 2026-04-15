# chat-platform-ingress-recommendation-v1

## Goal

Recommend which chat platform to use as an ingress for this stack, based on user type and operational fit.

## Core Rule

All chat platforms should stay thin.

- chat app = thin ingress
- Python control plane = business center
- Mac standby worker = execution fallback
- no duplicated YouTube / GitHub / routing logic inside the chat handler

## Recommendations by Scenario

### 1. Enterprise internal staff

Use **Feishu** first.

Why:

- it fits the "internal employee assistant" / "housekeeper" pattern better
- it supports private chat and `@bot` in group chat
- it is a natural enterprise work entry, not a forced consumer-chat wrapper
- it fits a long-running Linux control plane with Mac standby fallback

Best ingress shapes:

- private chat bot
- group `@bot`

### 2. Fastest thin ingress for YouTube automation

Use **Telegram** first.

Why:

- lower setup friction
- a direct fit for message -> URL -> `youtube_autoflow`
- already aligned with the current thin-ingress decision

### 3. Long-term external business messaging

Use **WhatsApp** when the business needs it.

Why:

- viable for real user-facing operations
- but heavier on business setup and operating constraints than Telegram
- better treated as a production-grade business channel than a lightweight shortcut

## Relative Preference

For this stack, the practical order is:

1. Feishu for internal corporate users
2. Telegram for quickest thin ingress
3. WhatsApp for external business-facing deployment

That order is about operational fit, not technical prestige.

## What Not To Do

- do not make each chat handler its own business pipeline
- do not split YouTube / GitHub logic by platform
- do not bind the channel choice to the execution worker identity
- do not let ingress choice change the control-plane source of truth

## Reusable Summary

> Feishu is the best fit for internal employees, Telegram is the fastest thin ingress, and WhatsApp is the heavier but viable business channel. In all three cases, the chat app should stay a thin entry point and the Python control plane should stay authoritative.

