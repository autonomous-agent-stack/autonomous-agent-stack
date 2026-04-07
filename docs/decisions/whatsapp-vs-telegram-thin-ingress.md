# whatsapp-vs-telegram-thin-ingress-v1

## Position

If the question is whether WhatsApp is a better replacement for Telegram in this stack, the answer is:

- not dramatically harder in code
- but moderately more annoying in platform setup and operational friction

The important point is architectural, not cosmetic: the hard part is no longer "which chat app receives the message". The hard part is already solved by keeping the main business flow in the Python control plane and treating chat apps as thin ingress layers.

## Why WhatsApp Is Slightly Heavier

Compared with Telegram, WhatsApp usually adds friction in these areas:

- account / number / business verification setup
- webhook configuration and validation
- business-platform-specific sending and conversation constraints
- heavier operational and compliance boundaries

That extra cost is not primarily in Mac standby workers, `youtube_autoflow`, GitHub publishing, or repository routing. Those should stay unchanged if the ingress is switched.

## Working Assumption

Keep the stack on this rule:

- chat app = thin ingress
- `youtube_autoflow` = single source of truth
- no duplicated business logic inside the WhatsApp or Telegram handler

In practical terms, both Telegram and WhatsApp should only do:

1. accept a message
2. extract a URL
3. hand off to `youtube_autoflow`
4. return immediate acceptance / rejection feedback

## Relative Cost

Practical engineering estimate:

- Telegram thin ingress: `1x`
- WhatsApp thin ingress: `1.5x` to `2x`

That multiplier is mostly platform setup, not core code changes.

## Recommendation

- If the goal is to get a chat entrypoint working quickly, Telegram is cheaper.
- If the goal is to serve real business users long-term, WhatsApp is viable, but it should not be treated as the lighter option.
- If both are supported, the shared core should remain the same and only the ingress adapter should change.

## Non-goals

- no WhatsApp-specific YouTube pipeline
- no duplicated GitHub publish path
- no business logic in the chat handler
- no change to `youtube_autoflow` ownership

## Reusable Summary

The shortest version is:

> WhatsApp is not a system rewrite for this architecture, but it is more work than Telegram. The extra cost is in platform access and operations, not in the control plane.

## Related Decision

- [Chat platform ingress recommendation](./chat-platform-ingress-recommendation-v1.md)
