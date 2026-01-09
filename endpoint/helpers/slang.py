"""Slang replacement functions for character-specific language."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern
    replacement: str


def _compile_rules(pairs: Iterable[tuple[str, str]]) -> list[Rule]:
    return [Rule(re.compile(p, re.IGNORECASE), r) for p, r in pairs]


BRETON_RULES = _compile_rules(
    [
        (r"\bau revoir\b", "Kenavo"),
        (r"\bsanté\b\s*!", "Yec'hed mat !"),
        (r"\bà la tienne\b\s*!", "Yec'hed mat !"),
        (r"\bbonjour\b", "Demat"),
        (r"\bmerci\b", "Trugarez"),
        (r"\bmon dieu\b\s*!", "Ma doué !"),
    ]
)

NORMAN_RULES = _compile_rules(
    [
        (r"\bbonjour\b", "Boujou"),
        (r"\bau revoir\b", "Boujou"),
        (r"\bmon dieu\b", "Ma mé"),
        (r"\boh\b", "Ben"),
        (r"\bnon\b", "Point"),
    ]
)


def apply_slang(text: str, rules: list[Rule], prob: float = 0.7, rng: Optional[random.Random] = None) -> str:
    """Randomly applies at most one slang replacement among rules that match."""
    if not text:
        return text

    rng = rng or random
    if rng.random() >= prob:
        return text

    matches = [rule for rule in rules if rule.pattern.search(text)]
    if not matches:
        return text

    rule = rng.choice(matches)
    return rule.pattern.sub(rule.replacement, text, count=1)


def apply_breton_slang(text: str, prob: float = 0.7, rng: Optional[random.Random] = None) -> str:
    return apply_slang(text, BRETON_RULES, prob=prob, rng=rng)


def apply_norman_slang(text: str, prob: float = 0.7, rng: Optional[random.Random] = None) -> str:
    return apply_slang(text, NORMAN_RULES, prob=prob, rng=rng)
