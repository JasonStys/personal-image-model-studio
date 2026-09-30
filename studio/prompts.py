"""Parse bounded numeric prompt weights and produce model-facing scene/region sections."""

# Index: declarations module.weighted@L11, module.words@L29, module.compile_prompt@L34, module.enforce_policy@L70; variables WEIGHT@L7, WORDS@L8, text@L11, spans@L15, start@L15, match@L16, weight@L18, start@L22, _@L24, value@L24, text@L26, weight@L26, text@L29, prompt@L34, positive@L36, k@L37, negative@L39, k@L41, regions@L44, subject@L45, description@L46, k@L47, positive@L58, negative@L59, text@L60, r@L63, r@L64, compiled@L70, denied@L70, text@L72, r@L74, value@L74, _@L75, span@L75, term@L77, phrase@L78. Purposes/parameters: docs/code-map.json.
import re
import unicodedata

WEIGHT = re.compile(r"\(([^():]{1,300}):([0-9]+(?:\.[0-9]+)?)\)")
WORDS = re.compile(r"[\w'-]+", re.UNICODE)


def weighted(text: str) -> list[tuple[str, float]]:
    """Return ordered plain/weighted spans; no nesting or implicit weighting is supported."""
    if len(text) > 10000:
        raise ValueError("Compiled prompt is too long")
    spans, start = [], 0
    for match in WEIGHT.finditer(text):
        spans.append((text[start : match.start()], 1.0))
        weight = float(match.group(2))
        if not 0.1 <= weight <= 2.0:
            raise ValueError("Prompt weights must be between 0.1 and 2")
        spans.append((match.group(1), weight))
        start = match.end()
    spans.append((text[start:], 1.0))
    if any("(" in value or ")" in value for value, _ in spans):
        raise ValueError("Use only the supported (phrase:1.2) syntax, without nesting")
    return [(text, weight) for text, weight in spans if text.strip()]


def words(text: str) -> list[str]:
    """Normalize Unicode and split words consistently in training, prompts and glossary lookup."""
    return WORDS.findall(unicodedata.normalize("NFKC", text).casefold())


def compile_prompt(prompt: dict) -> dict:
    """Preserve independent negative and spatial sections; names are labels, not learned tokens."""
    positive = ", ".join(
        prompt.get(k, "") for k in ("description", "style", "tags") if prompt.get(k)
    )
    negative = ", ".join(
        prompt.get(k, "")
        for k in ("negative_description", "negative_style", "negative_tags")
        if prompt.get(k)
    )
    regions = []
    for subject in prompt.get("subjects", []):
        description = ", ".join(
            subject.get(k, "") for k in ("description", "tags", "framing") if subject.get(k)
        )
        if subject.get("region"):
            regions.append(
                {
                    "positive": description,
                    "negative": subject.get("negative", ""),
                    "box": subject["region"],
                }
            )
        else:
            positive += ", " + description
            negative += ", " + subject.get("negative", "")
    for text in [
        positive,
        negative,
        *[r["positive"] for r in regions],
        *[r["negative"] for r in regions],
    ]:
        weighted(text)
    return {"positive": positive.strip(", "), "negative": negative.strip(", "), "regions": regions}


def enforce_policy(compiled: dict, denied: list[str]) -> None:
    """Apply operator phrase blocks to visible positive text; this is not a visual safety classifier."""
    text = " ".join(
        " ".join(words(span))
        for value in [compiled["positive"], *[r["positive"] for r in compiled["regions"]]]
        for span, _ in weighted(value)
    )
    for term in denied:
        phrase = " ".join(words(term))
        if phrase and f" {phrase} " in f" {text} ":
            raise ValueError("Prompt blocked by the local phrase policy")
