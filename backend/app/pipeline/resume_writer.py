"""
Resume Writer — compiles generated bullet points from multiple sections into
the final ordered, deduplicated set, with optional LLM-based polish.

Flow:
  1. Filter empty sections
  2. Deduplicate overlapping bullets across sections (Jaccard similarity > 80 % )
  3. Order sections per profile preference
  4. Optionally polish via LLM (resume_writeup.j2 template)
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Optional

from app.models.application import BulletPoint, SectionPoints
from app.models.profile import UserProfile
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# Default section ordering — used as fallback when profile.section_order is empty.
_DEFAULT_SECTION_ORDER: list[str] = [
    "education",
    "skills",
    "projects",
    "experience",
    "publications",
    "leadership",
    "certifications",
]

# Maps section_key prefixes to canonical section_order keys.
# e.g. "project:abc123" → "projects", "experience:xyz" → "experience".
_SECTION_KEY_MAP: dict[str, str] = {
    "project": "projects",
    "experience": "experience",
}


class ResumeWriter:
    """Compiles bullet points into a final ordered, deduplicated set.

    Usage:
        writer = ResumeWriter(llm_service, prompt_manager)
        compiled = await writer.compile_resume(sections, profile, ...)
    """

    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager) -> None:
        """Initialize the ResumeWriter.

        Args:
            llm_service: Provider-agnostic LLM client for optional polish step.
            prompt_manager: Loads Jinja2 prompt templates for LLM calls.
        """
        self.llm = llm_service
        self.prompts = prompt_manager

    # ── Public API ──────────────────────────────────────────────────────────

    async def compile_resume(
        self,
        sections: list[SectionPoints],
        profile: UserProfile,
        job_title: str,
        company_name: str,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> list[SectionPoints]:
        """Compile sections into the final ordered, deduplicated set.

        Pipeline steps:
        1. Filter out any sections that have no bullets.
        2. Deduplicate overlapping / near-identical bullets across sections.
        3. Order sections according to the profile's ``section_order``.
        4. Optionally call the LLM for a final polish pass (if the
           ``resume_writeup`` template is available).

        Args:
            sections: List of ``SectionPoints`` from the generation pipeline.
            profile: ``UserProfile`` containing section ordering preferences.
            job_title: Target job title (used as LLM context during polish).
            company_name: Target company name (used as LLM context during polish).
            on_token: Optional async callback invoked per token during the LLM
                      streaming response. Signature: ``(token_text)``.

        Returns:
            Compiled list of ``SectionPoints``, ordered and deduplicated.
            Returns an empty list when *sections* is empty or all sections
            have no bullets.
        """
        # Step 1 — filter out sections with no bullets
        non_empty = [s for s in sections if s.bullets]

        if not non_empty:
            logger.info("No sections with bullets to compile — returning empty list")
            return []

        logger.debug(
            "Compiling %d non-empty sections (from %d total)",
            len(non_empty),
            len(sections),
        )

        # Step 2 — deduplicate overlapping bullets across sections
        deduped = self.deduplicate(non_empty, profile.section_order)

        # Step 3 — order sections per profile preference
        ordered = self.order_sections(deduped, profile)

        # Step 4 — optional LLM polish
        if self._has_writeup_template():
            logger.info("LLM polish enabled — calling LLM for resume write-up")
            polished = await self._polish_with_llm(
                sections=ordered,
                profile=profile,
                job_title=job_title,
                company_name=company_name,
                on_token=on_token,
            )
            return polished

        return ordered

    def deduplicate(
        self,
        sections: list[SectionPoints],
        section_order: Optional[list[str]] = None,
    ) -> list[SectionPoints]:
        """Remove bullets with >80% Jaccard similarity across sections.

        Compares every pair of bullets from *different* sections. When the
        Jaccard similarity of their word sets exceeds 0.8, the bullet from
        the less relevant section (lower in *section_order*) is removed.

        .. note::
           Bullets within the same section are never compared — they are
           assumed to be distinct by construction.

        Args:
            sections: List of ``SectionPoints`` to deduplicate.
            section_order: Ordered list of section keys where earlier position
                           means higher relevance.  Falls back to
                           ``_DEFAULT_SECTION_ORDER`` when ``None``.

        Returns:
            Sections with duplicate bullets removed. Sections that become
            empty after removal are omitted from the result.
        """
        if len(sections) <= 1:
            return sections

        order = section_order or _DEFAULT_SECTION_ORDER

        # Flatten all bullets across sections into a comparable index.
        # Each entry stores the section index, bullet index, bullet text,
        # and the relevance rank of its parent section.
        all_entries: list[dict] = []
        for sec_idx, section in enumerate(sections):
            rank = _section_rank(section.section_key, order)
            for bul_idx, bullet in enumerate(section.bullets):
                all_entries.append(
                    {
                        "sec_idx": sec_idx,
                        "bul_idx": bul_idx,
                        "bullet": bullet,
                        "rank": rank,
                    }
                )

        # Identify duplicate pairs across sections.
        bullets_to_remove: set[tuple[int, int]] = set()  # (sec_idx, bul_idx)

        for i in range(len(all_entries)):
            for j in range(i + 1, len(all_entries)):
                entry_i = all_entries[i]
                entry_j = all_entries[j]

                # Only compare bullets from different sections.
                if entry_i["sec_idx"] == entry_j["sec_idx"]:
                    continue

                similarity = _jaccard_similarity(
                    entry_i["bullet"].text,
                    entry_j["bullet"].text,
                )

                if similarity > 0.8:
                    # Keep the bullet from the more relevant section
                    # (lower rank = earlier in section_order = higher priority).
                    if entry_i["rank"] <= entry_j["rank"]:
                        bullets_to_remove.add(
                            (entry_j["sec_idx"], entry_j["bul_idx"])
                        )
                    else:
                        bullets_to_remove.add(
                            (entry_i["sec_idx"], entry_i["bul_idx"])
                        )

        if not bullets_to_remove:
            return sections

        logger.info(
            "Deduplication removed %d bullet(s) across sections",
            len(bullets_to_remove),
        )

        # Rebuild sections excluding removed bullets.
        result: list[SectionPoints] = []
        for sec_idx, section in enumerate(sections):
            kept = [
                bullet
                for bul_idx, bullet in enumerate(section.bullets)
                if (sec_idx, bul_idx) not in bullets_to_remove
            ]
            if kept:
                result.append(
                    SectionPoints(
                        section_key=section.section_key,
                        section_title=section.section_title,
                        bullets=kept,
                    )
                )

        return result

    def order_sections(
        self,
        sections: list[SectionPoints],
        profile: UserProfile,
    ) -> list[SectionPoints]:
        """Order sections according to the profile's ``section_order``.

        Sorting strategy (stable sort, so ties preserve original order):

        * Keys that appear verbatim in ``section_order`` are placed by their
          index.
        * Keys prefixed with a known type (e.g. ``"project:abc123"`` →
          ``"projects"``) map to the corresponding entry.
        * Unrecognized keys are appended after all known sections.

        Args:
            sections: List of ``SectionPoints`` to reorder.
            profile: ``UserProfile`` whose ``section_order`` field drives the
                     ordering.

        Returns:
            Sections sorted according to the profile's preferences.
        """
        order = profile.section_order or _DEFAULT_SECTION_ORDER

        def sort_key(section: SectionPoints) -> tuple[int, int]:
            return (_section_rank(section.section_key, order), 0)

        return sorted(sections, key=sort_key)

    # ── Private helpers ─────────────────────────────────────────────────────

    def _has_writeup_template(self) -> bool:
        """Return ``True`` if the ``resume_writeup`` prompt template exists."""
        return "resume_writeup" in self.prompts.list_templates()

    async def _polish_with_llm(
        self,
        sections: list[SectionPoints],
        profile: UserProfile,
        job_title: str,
        company_name: str,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> list[SectionPoints]:
        """Send sections to the LLM for final organisation and polish.

        Uses the ``resume_writeup.j2`` template to build the prompt.  The LLM
        is expected to return a JSON array of section objects.  If the LLM
        response cannot be parsed, the original *sections* are returned as a
        fallback.
        """
        context = {
            "user_name": profile.name,
            "job_title": job_title,
            "company_name": company_name,
            "section_order": profile.section_order or _DEFAULT_SECTION_ORDER,
            "sections": [
                {
                    "section_key": s.section_key,
                    "section_title": s.section_title,
                    "bullets": s.bullets,
                }
                for s in sections
            ],
        }

        prompt = self.prompts.render("resume_writeup", context)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a resume compilation expert. "
                    "Output ONLY valid JSON — no markdown fences, no explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        if on_token is not None:
            # ── Streaming path ──
            full_text = ""
            stream = await self.llm.generate(
                messages=messages,
                task="resume_writeup",
                temperature=0.3,
                stream=True,
            )
            async for token in stream:
                full_text += token
                await on_token(token)

            parsed = _parse_llm_response(full_text)
            if parsed is not None:
                return parsed
            logger.warning(
                "Failed to parse streamed LLM response — "
                "falling back to original sections"
            )
            return sections
        else:
            # ── Non-streaming path ──
            result = await self.llm.generate(
                messages=messages,
                task="resume_writeup",
                temperature=0.3,
                stream=False,
            )
            parsed = _parse_llm_response(result)
            if parsed is not None:
                return parsed
            logger.warning(
                "Failed to parse LLM response for resume write-up — "
                "falling back to original sections"
            )
            return sections


# ── Module-level helpers (stateless, easy to unit-test) ────────────────────


def _normalize(text: str) -> set[str]:
    """Normalise text for similarity comparison.

    1. Lowercase
    2. Remove punctuation (keep ``[a-z0-9]`` and whitespace)
    3. Split on whitespace → set of words

    Args:
        text: Raw input string.

    Returns:
        Set of normalised words.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return set(text.split())


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute the Jaccard similarity coefficient of two strings.

    ``similarity = |A ∩ B| / |A ∪ B|``

    Edge cases:
    * Both empty → ``1.0`` (identical).
    * One empty, one not → ``0.0``.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Float in ``[0.0, 1.0]``.
    """
    words_a = _normalize(text_a)
    words_b = _normalize(text_b)

    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _section_rank(section_key: str, order: list[str]) -> int:
    """Determine the ordering rank of a section key.

    Lower rank = higher priority (appears earlier in the compiled resume).

    Matching strategy:
    1. Verbatim match in *order* → return its index.
    2. Prefix match via ``_SECTION_KEY_MAP`` (e.g. ``"project:id"`` →
       ``"projects"``) → return the mapped key's index.
    3. No match → return ``len(order)`` (after all known sections).

    Args:
        section_key: The section key to rank (e.g. ``"experience:acme"``).
        order: Ordered list of canonical section keys.

    Returns:
        Integer rank (lower = earlier).
    """
    if section_key in order:
        return order.index(section_key)

    for prefix, mapped_key in _SECTION_KEY_MAP.items():
        if section_key.startswith(f"{prefix}:") and mapped_key in order:
            return order.index(mapped_key)

    return len(order)


def _parse_llm_response(text: str) -> Optional[list[SectionPoints]]:
    """Parse the LLM's JSON response into a list of ``SectionPoints``.

    Handles common LLM quirks:
    * Markdown code fences (`` ```json … ``` ``)
    * Missing or extra fields
    * Bullets returned as plain strings *or* ``BulletPoint`` dicts

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed ``SectionPoints`` list, or ``None`` if parsing fails.
    """
    try:
        text = text.strip()

        # Strip markdown code fences.
        if text.startswith("```"):
            start = text.find("\n") + 1
            end = text.rfind("```")
            if end > start:
                text = text[start:end].strip()

        # Also handle ```json prefix.
        if text.startswith("```json"):
            text = text[7:]
            end = text.rfind("```")
            if end > 0:
                text = text[:end].strip()

        data = json.loads(text)

        if not isinstance(data, list):
            logger.warning("LLM response root is not a JSON list — expected list of sections")
            return None

        parsed: list[SectionPoints] = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning("Item %d in LLM response is not a dict — skipping", idx)
                continue

            section_key = item.get("section_key", "")
            section_title = item.get("section_title", "")
            bullets_data = item.get("bullets", [])

            bullets: list[BulletPoint] = []
            for i, b in enumerate(bullets_data):
                if isinstance(b, dict):
                    bullets.append(BulletPoint(**b))
                elif isinstance(b, str):
                    bullets.append(
                        BulletPoint(
                            id=f"polished-{section_key}-{i}",
                            section=section_key,
                            text=b,
                            order=i,
                        )
                    )

            parsed.append(
                SectionPoints(
                    section_key=section_key,
                    section_title=section_title,
                    bullets=bullets,
                )
            )

        logger.info(
            "LLM polish returned %d section(s) with %d total bullet(s)",
            len(parsed),
            sum(len(s.bullets) for s in parsed),
        )
        return parsed

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "Failed to parse LLM response for resume write-up: %s — "
            "falling back to original sections",
            exc,
        )
        return None
