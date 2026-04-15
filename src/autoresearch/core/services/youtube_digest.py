from __future__ import annotations

import json
import re

from autoresearch.shared.models import (
    YouTubeDigestRead,
    YouTubeQuestionAnswerRead,
    YouTubeTranscriptRead,
    YouTubeVideoRead,
    utc_now,
)


class YouTubeDigestService:
    """Deterministic digest and Q&A helpers for the YouTube agent v1."""

    _SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")
    _GENERIC_CONTEXT_PREFIX_RE = re.compile(
        r"^(?:in this (?:video|session)|today|here)\s*,?\s*",
        re.IGNORECASE,
    )
    _GENERIC_FRAMING_ACTION_RE = re.compile(
        r"^(?:(?:we|i)(?:'ll| will| are going to| am going to)|let'?s)\s+"
        r"(?:take a (?:tour|look)|explore|cover|dive into|talk about)\b",
        re.IGNORECASE,
    )
    _SUBSTANTIVE_FRAMING_MARKER_RE = re.compile(
        r"\b("
        r"how|why|compare|comparison|versus|vs\.?|trade[- ]?off|steps?|"
        r"architecture|pipeline|state|idempotenc(?:y|e)|transcript|digest|metadata|"
        r"subscription|discovery|failure|reason|retryable|build(?:ing)? an?|built with|using"
        r")\b",
        re.IGNORECASE,
    )
    _DISCOURSE_PREFIX_RE = re.compile(r"^(?:so|and|now)\s+", re.IGNORECASE)
    _ENTITY_APPOSITIVE_RE = re.compile(
        r'^(?P<entity>"[^"]+?"|[A-Z][A-Za-z0-9 .+\-]{1,60}),\s+(?P<rest>(?:an?|the)\b.+)$'
    )
    _LEADING_NOISE_PATTERNS = (
        re.compile(r"^(?:hey|hi|hello|good (?:morning|afternoon|evening)|what'?s up)\b[^.!?。！？]{0,80}", re.IGNORECASE),
        re.compile(r"^welcome back(?: to (?:the )?(?:channel|video))?\b[^.!?。！？]{0,80}", re.IGNORECASE),
        re.compile(r"^before we (?:get started|jump in|dive in)\b[^.!?。！？]{0,80}", re.IGNORECASE),
        re.compile(r"^without further ado\b[^.!?。！？]{0,80}", re.IGNORECASE),
        re.compile(r"^(?:if you'?re new here[, ]*)?(?:my name is|i am|i'm)\b[^.!?。！？]{0,80}", re.IGNORECASE),
        re.compile(r"^before [a-z0-9 .'\-]{2,40}, i (?:was|worked|built|led)\b[^.!?。！？]{0,100}", re.IGNORECASE),
        re.compile(r"^have you ever (?:imagined|wondered)\b[^.!?。！？]{0,120}", re.IGNORECASE),
    )
    _TRAILING_NOISE_PATTERNS = (
        re.compile(r"(?:please )?(?:like|subscribe|comment)\b.*$", re.IGNORECASE),
        re.compile(r"(?:hit|smash) (?:the )?(?:bell|like button)\b.*$", re.IGNORECASE),
        re.compile(r"thanks for watching\b.*$", re.IGNORECASE),
        re.compile(r"see you (?:in the next video|next time)\b.*$", re.IGNORECASE),
        re.compile(r"check out (?:the )?links? below\b.*$", re.IGNORECASE),
    )
    _LOW_VALUE_SENTENCE_PATTERNS = (
        re.compile(r"^or if you prefer\b.*$", re.IGNORECASE),
        re.compile(r"^you can also explore\b.*$", re.IGNORECASE),
        re.compile(r"^explore our solution\b.*$", re.IGNORECASE),
        re.compile(r"^inspect the full architecture\b.*$", re.IGNORECASE),
        re.compile(r"^quiz your knowledge\b.*$", re.IGNORECASE),
        re.compile(r"^what will you create next\b.*$", re.IGNORECASE),
        re.compile(r"^(?:and )?we can'?t wait to see\b.*$", re.IGNORECASE),
    )
    _INLINE_NOISE_PATTERNS = (
        re.compile(r"\bthis video is sponsored by\b", re.IGNORECASE),
        re.compile(r"\bthanks to .{1,40} for sponsoring\b", re.IGNORECASE),
        re.compile(r"\btoday'?s sponsor\b", re.IGNORECASE),
        re.compile(r"\bbrought to you by\b", re.IGNORECASE),
        re.compile(r"\bpromo code\b", re.IGNORECASE),
        re.compile(r"\bdiscount code\b", re.IGNORECASE),
        re.compile(r"\baffiliate link\b", re.IGNORECASE),
        re.compile(r"\buse code [A-Z0-9_-]{3,}\b", re.IGNORECASE),
        re.compile(r"\bif you'?re new here\b", re.IGNORECASE),
        re.compile(r"\bwelcome back to (?:the )?channel\b", re.IGNORECASE),
        re.compile(r"\blet'?s jump right in\b", re.IGNORECASE),
        re.compile(r"\byou have found your solution\b", re.IGNORECASE),
    )

    def generate_digest(
        self,
        *,
        video: YouTubeVideoRead,
        transcript: YouTubeTranscriptRead | None,
        output_format: str = "markdown",
    ) -> str:
        summary_lines = self._build_summary_lines(video=video, transcript=transcript, limit=3)
        key_points = self._build_key_points(video=video, transcript=transcript, limit=5)

        if output_format == "json":
            payload = {
                "video_id": video.video_id,
                "title": video.title,
                "channel_title": video.channel_title,
                "summary": summary_lines,
                "key_points": key_points,
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

        summary_block = "\n".join(f"- {line}" for line in summary_lines) or "- 暂无可用摘要内容"
        key_points_block = "\n".join(f"- {line}" for line in key_points) or "- 暂无可用关键点"

        return (
            f"# {video.title or video.video_id}\n\n"
            f"## Video\n"
            f"- Video ID: `{video.video_id}`\n"
            f"- Channel: {video.channel_title or 'unknown'}\n"
            f"- Source: {video.source_url}\n\n"
            f"## Summary\n"
            f"{summary_block}\n\n"
            f"## Key Points\n"
            f"{key_points_block}\n"
        )

    def answer_question(
        self,
        *,
        video: YouTubeVideoRead,
        question: str,
        transcript: YouTubeTranscriptRead | None,
        digest: YouTubeDigestRead | None,
    ) -> YouTubeQuestionAnswerRead:
        summary_lines = self._build_summary_lines(video=video, transcript=transcript, limit=3)
        corpus_parts: list[str] = []
        if video.title:
            corpus_parts.append(video.title)
        if video.description:
            corpus_parts.append(video.description)
        if transcript and transcript.content.strip():
            corpus_parts.append(transcript.content)
        elif digest and digest.content.strip():
            corpus_parts.append(digest.content)
        corpus = "\n".join(part for part in corpus_parts if part)

        candidate_lines = self._rank_lines(question=question, corpus=corpus)
        citations = candidate_lines or summary_lines
        if self._is_summary_question(question):
            lead = video.title or "这期视频"
            supporting_lines = summary_lines or candidate_lines
            citations = supporting_lines[:3]
            if supporting_lines:
                answer = f"这期视频主要讲《{lead}》。重点包括：\n" + "\n".join(
                    f"- {line}" for line in supporting_lines[:3]
                )
            else:
                answer = f"这期视频主要讲《{lead}》，但当前可用字幕和描述不足，无法再给出更细的要点。"
        elif candidate_lines:
            answer = "基于当前可用内容，最相关的信息是：\n" + "\n".join(f"- {line}" for line in candidate_lines)
        else:
            answer = "当前还没有足够的字幕或摘要内容，暂时无法可靠回答这个问题。"

        return YouTubeQuestionAnswerRead(
            video_id=video.video_id,
            question=question,
            answer=answer,
            citations=citations,
            created_at=utc_now(),
            metadata={"source": "deterministic-v1"},
        )

    def _build_summary_lines(
        self,
        *,
        video: YouTubeVideoRead,
        transcript: YouTubeTranscriptRead | None,
        limit: int,
    ) -> list[str]:
        lines = self._description_lines(video.description)
        lines.extend(self._normalize_lines(transcript.content if transcript else ""))
        return self._dedupe(lines)[:limit]

    def _build_key_points(
        self,
        *,
        video: YouTubeVideoRead,
        transcript: YouTubeTranscriptRead | None,
        limit: int,
    ) -> list[str]:
        transcript_lines = self._normalize_lines(transcript.content if transcript else "")
        description_lines = self._description_lines(video.description)
        combined = transcript_lines + description_lines
        if video.title:
            combined = self._sort_by_title_relevance(video.title, combined)
        return self._dedupe(combined)[:limit]

    def _rank_lines(self, *, question: str, corpus: str) -> list[str]:
        lines = self._normalize_lines(corpus)
        if not lines:
            return []

        tokens = {
            token for token in re.findall(r"[\w-]+", question.lower())
            if len(token) >= 2
        }
        scored: list[tuple[int, str]] = []
        for line in lines:
            lowered = line.lower()
            score = sum(1 for token in tokens if token in lowered)
            if score > 0:
                scored.append((score, line))

        if scored:
            scored.sort(key=lambda item: (-item[0], len(item[1])))
            return [line for _, line in scored[:3]]
        return self._prefer_informative(lines)[:3]

    def _normalize_lines(self, corpus: str) -> list[str]:
        sentences = self._extract_sentences(corpus)
        lines: list[str] = []
        seen: set[str] = set()
        total = len(sentences)
        for index, sentence in enumerate(sentences):
            line = self._clean_sentence(sentence)
            if len(line) < 20:
                continue
            if self._is_noise_line(line, index=index, total=total):
                continue
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)
        return lines

    def _extract_sentences(self, corpus: str) -> list[str]:
        if not corpus.strip():
            return []

        chunks: list[str] = []
        current: list[str] = []
        for raw_line in corpus.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            cleaned = self._clean_fragment(line)
            if not cleaned:
                continue
            if self._is_disposable_fragment(cleaned):
                continue
            for fragment in self._split_inline_sentences(cleaned):
                current.append(fragment)
                if re.search(r"[.!?。！？:：]$", fragment):
                    chunks.append(" ".join(current))
                    current = []
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _split_inline_sentences(self, fragment: str) -> list[str]:
        parts = [part.strip() for part in self._SENTENCE_SPLIT_RE.split(fragment) if part.strip()]
        return parts or [fragment]

    def _clean_fragment(self, fragment: str) -> str:
        fragment = " ".join(fragment.split())
        fragment = re.sub(r"^\[[^\]]+\]$", "", fragment).strip()
        fragment = re.sub(r"^[A-Z][A-Z0-9 .'-]{1,40}:\s*", "", fragment).strip()
        fragment = re.sub(r"\s+", " ", fragment)
        return fragment

    def _clean_sentence(self, sentence: str) -> str:
        sentence = re.sub(r"\s+", " ", sentence).strip(" -")
        sentence = re.sub(r"^[,.;:]+", "", sentence).strip()
        sentence = self._rewrite_generic_framing(sentence)
        if not sentence:
            return ""
        if any(pattern.match(sentence) for pattern in self._LEADING_NOISE_PATTERNS):
            return ""
        for pattern in self._TRAILING_NOISE_PATTERNS:
            sentence = pattern.sub("", sentence).rstrip(" ,.;:-")
        return sentence

    def _rewrite_generic_framing(self, sentence: str) -> str:
        had_context_prefix = False
        updated = self._GENERIC_CONTEXT_PREFIX_RE.sub("", sentence)
        if updated != sentence:
            sentence = updated
            had_context_prefix = True
            sentence = self._capitalize_sentence_start(sentence)

        updated = self._DISCOURSE_PREFIX_RE.sub("", sentence).strip()
        if updated != sentence:
            sentence = self._capitalize_sentence_start(updated)
        else:
            sentence = updated
        sentence = re.sub(r"^(?:that'?s|meet)\s+", "", sentence, flags=re.IGNORECASE)
        sentence = re.sub(r'^"([^"]+),"\s+', r'"\1", ', sentence).strip()

        appositive = self._ENTITY_APPOSITIVE_RE.match(sentence)
        if appositive:
            sentence = f"{appositive.group('entity')} is {appositive.group('rest')}"

        if (
            had_context_prefix
            and self._GENERIC_FRAMING_ACTION_RE.match(sentence)
            and not self._SUBSTANTIVE_FRAMING_MARKER_RE.search(sentence)
        ):
            return ""
        return sentence.strip()

    def _capitalize_sentence_start(self, sentence: str) -> str:
        stripped = sentence.strip()
        if stripped and stripped[0].islower():
            return f"{stripped[0].upper()}{stripped[1:]}"
        return stripped

    def _is_disposable_fragment(self, fragment: str) -> bool:
        lowered = fragment.lower()
        return (
            "http://" in lowered
            or "https://" in lowered
            or lowered.startswith("resources:")
            or lowered.startswith("speaker:")
            or lowered.startswith("products mentioned:")
        )

    def _description_lines(self, description: str | None) -> list[str]:
        if not description:
            return []
        return self._normalize_lines(description)

    def _is_noise_line(self, line: str, *, index: int, total: int) -> bool:
        lowered = line.lower()
        noise_markers = (
            "http://",
            "https://",
            "subscribe to ",
            "learn more here",
            "resources:",
            "speaker:",
            "products mentioned:",
        )
        if any(marker in lowered for marker in noise_markers):
            return True
        if any(pattern.match(line) for pattern in self._LOW_VALUE_SENTENCE_PATTERNS):
            return True
        if any(pattern.search(line) for pattern in self._INLINE_NOISE_PATTERNS):
            return True
        if index <= 1 and any(pattern.match(line) for pattern in self._LEADING_NOISE_PATTERNS):
            return True
        if total and index >= max(total - 2, 0) and any(pattern.search(line) for pattern in self._TRAILING_NOISE_PATTERNS):
            return True
        return False

    def _sort_by_title_relevance(self, title: str, lines: list[str]) -> list[str]:
        title_tokens = {
            token for token in re.findall(r"[\w-]+", title.lower())
            if len(token) >= 3
        }
        if not title_tokens:
            return lines
        scored: list[tuple[int, int, str]] = []
        for index, line in enumerate(lines):
            lowered = line.lower()
            score = sum(1 for token in title_tokens if token in lowered)
            scored.append((score, index, line))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [line for _, _, line in scored]

    def _prefer_informative(self, lines: list[str]) -> list[str]:
        scored: list[tuple[int, str]] = []
        for line in lines:
            alpha_words = sum(1 for token in re.findall(r"[A-Za-z\u4e00-\u9fff0-9-]+", line) if len(token) >= 3)
            scored.append((alpha_words, line))
        scored.sort(key=lambda item: (-item[0], len(item[1])))
        return [line for _, line in scored]

    def _dedupe(self, lines: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for line in lines:
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(line)
        return deduped

    def _is_summary_question(self, question: str) -> bool:
        lowered = question.lower()
        patterns = (
            "mainly about",
            "what is this video about",
            "what is this about",
            "summary",
            "summarize",
            "讲什么",
            "主要讲",
            "主要内容",
            "总结",
        )
        return any(pattern in lowered for pattern in patterns)
