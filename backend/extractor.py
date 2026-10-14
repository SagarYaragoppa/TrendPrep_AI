import os
import re
import shutil

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

MAJOR_QUESTION_PATTERN = re.compile(r"(?mi)^\s*(Q\.?\s*)?(\d+)\)")
SUBQUESTION_PATTERN = re.compile(r"(?mi)^\s*([a-z])\)")
NOISE_LINE_PATTERNS = [
    re.compile(r"^\s*seat\s*no\.?\s*:?\s*$", re.I),
    re.compile(r"^\s*p\.?t\.?o\.?\s*$", re.I),
    re.compile(r"^\s*\[\d{4,}\].*$"),
    re.compile(r"^\s*pb-\d+.*$", re.I),
    re.compile(r"^\s*p-\d+.*$", re.I),
    re.compile(r"^\s*total no\. of.*$", re.I),
    re.compile(r"^\s*instructions? to the candidates.*$", re.I),
]
QUESTION_START_WORDS = (
    "what", "how", "why", "when", "which", "who", "explain", "define", "compare",
    "discuss", "describe", "write", "state", "evaluate", "illustrate", "list",
    "differentiate", "classify", "comment", "derive", "calculate", "find",
    "determine", "identify", "compute", "estimate", "predict", "draw", "give",
    "mention",
)
COMPOUND_QUESTION_PATTERN = re.compile(
    r"(?i)(?:(?<=\?)|(?<=\.)|(?<=;)|(?<=:))\s+(?=(?:what|how|why|when|which|who|explain|define|compare|discuss|describe|write|state|evaluate|illustrate|list|differentiate|classify|comment|derive|calculate|find|determine|identify|compute|estimate|predict|draw|give|mention)\b)"
)
FOLLOW_UP_START_PATTERN = re.compile(
    r"(?i)^(?:how|what|why|when|which|who|explain|describe|discuss|state|evaluate|list)\s+(?:it|they|this|these|its|their)\b"
)
INLINE_ENUMERATION_PATTERN = re.compile(r"(?i)\b(?:i{1,3}|iv|v)\)\s*")
_TESSERACT_READY = None


def _configure_tesseract() -> bool:
    global _TESSERACT_READY
    if _TESSERACT_READY is not None:
        return _TESSERACT_READY

    candidates = [
        os.getenv("TESSERACT_CMD"),
        os.path.join(os.path.dirname(__file__), "..", "tools", "tesseract", "tesseract.exe"),
        shutil.which("tesseract"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = os.path.abspath(candidate)
            _TESSERACT_READY = True
            return True

    _TESSERACT_READY = False
    return False

def extract_text(filepath: str) -> str:
    """Extracts text from a PDF or an Image."""
    if filepath.lower().endswith('.pdf'):
        return _extract_from_pdf(filepath)
    elif filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
        return _extract_from_image(filepath)
    else:
        raise ValueError("Unsupported file type")


def extract_relevant_text(filepath: str, syllabus: str) -> str:
    """Extract only the paper that best matches the current syllabus from a bundled exam PDF."""
    if filepath.lower().endswith(".pdf"):
        return _extract_relevant_from_pdf(filepath, syllabus)
    return extract_text(filepath)

def _extract_from_pdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    full_text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if not text.strip():
            # OCR fallback for scanned PDFs
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = _ocr_image(img)
        full_text += text + "\n"
    return full_text


def _extract_relevant_from_pdf(filepath: str, syllabus: str) -> str:
    doc = fitz.open(filepath)
    page_texts = [_extract_page_text(doc.load_page(i)) for i in range(len(doc))]
    windows = _candidate_paper_windows(page_texts)
    if not windows:
        return "\n".join(page_texts)

    syllabus_tokens = _syllabus_focus_tokens(syllabus)
    best_score = None
    best_window = None
    for start, end in windows:
        first_page = page_texts[start].lower()
        combined = "\n".join(page_texts[start:end + 1]).lower()
        title_score = 0
        if "data science and big data analytics" in first_page:
            title_score += 8
        if re.search(r"\bdata science\b", first_page):
            title_score += 4
        if "artificial intelligence" in first_page and "data science and big data analytics" not in first_page:
            title_score -= 2

        token_score = _count_focus_hits(combined, syllabus_tokens)
        score = title_score + token_score
        if best_score is None or score > best_score:
            best_score = score
            best_window = (start, end)

    if best_window is None:
        return "\n".join(page_texts)

    start, end = best_window
    return "\n".join(page_texts[start:end + 1])

def _extract_from_image(filepath: str) -> str:
    img = Image.open(filepath)
    return _ocr_image(img)


def _extract_page_text(page) -> str:
    text = page.get_text()
    if text.strip():
        return text

    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return _ocr_image(img)


def _candidate_paper_windows(page_texts: list[str]) -> list[tuple[int, int]]:
    windows = []
    for index, text in enumerate(page_texts):
        lowered = text.lower()
        if "total no. of questions" not in lowered and "total no.of questions" not in lowered:
            continue
        total_pages = _parse_total_pages(text)
        if total_pages is None:
            continue
        end = min(len(page_texts) - 1, index + total_pages - 1)
        windows.append((index, end))
    return windows


def _parse_total_pages(text: str) -> int | None:
    match = re.search(r"total\s+no\.?\s+of\s+pages\s*:\s*(\d+)", text, re.I)
    if match:
        return int(match.group(1))
    return None


def _syllabus_focus_tokens(syllabus: str) -> set[str]:
    stop_words = {
        "unit", "introduction", "overview", "applications", "application", "examples", "example",
        "methods", "method", "techniques", "technique", "using", "learning", "analysis", "model",
        "models", "system", "systems", "process", "processes", "basics", "concepts", "concept",
        "data", "mining", "intelligence",
    }
    tokens = set()
    for raw_line in syllabus.splitlines():
        line = raw_line.strip().lower()
        if not line:
            continue
        if line.startswith("unit "):
            line = re.sub(r"^unit\s+\w+\s+", "", line)
        line = line.replace("â€“", " ").replace("Ã¢â‚¬â€œ", " ")
        words = [word for word in re.findall(r"[a-z][a-z0-9]+", line) if len(word) > 3 and word not in stop_words]
        for index, word in enumerate(words):
            tokens.add(word)
            if index + 1 < len(words):
                tokens.add(f"{word} {words[index + 1]}")
    return tokens


def _count_focus_hits(text: str, tokens: set[str]) -> int:
    score = 0
    for token in tokens:
        score += len(re.findall(re.escape(token), text))
    return score


def _ocr_image(img: Image.Image) -> str:
    if not _configure_tesseract():
        return ""

    try:
        return pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError:
        return ""

def extract_questions_from_text(text: str) -> list[str]:
    """Extract question-like subparts from raw paper text."""
    normalized_text = _normalize_text(text)
    major_blocks = _split_major_questions(normalized_text)

    questions = []
    for _, block in major_blocks:
        questions.extend(_split_subquestions(block))

    return [q for q in questions if _looks_like_question(q)]

def _normalize_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue

        if any(pattern.match(line) for pattern in NOISE_LINE_PATTERNS):
            continue

        if line.upper() in {"OR", "SECTION-I", "SECTION-II"}:
            continue

        # Drop decorative or OCR-noisy lines.
        if len(re.sub(r"[\W_]+", "", line)) <= 2:
            continue

        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned

def _split_major_questions(text: str) -> list[tuple[str, str]]:
    matches = list(MAJOR_QUESTION_PATTERN.finditer(text))
    if not matches:
        return [("", text)]

    blocks = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        q_number = match.group(2)
        block = text[start:end].strip()
        blocks.append((q_number, block))
    return blocks

def _split_subquestions(block: str) -> list[str]:
    body = re.sub(r"(?mi)^\s*(Q\.?\s*)?\d+\)\s*", "", block, count=1).strip()
    body = re.sub(r"(?<!^)\s+([a-z])\)", r"\n\1)", body)
    matches = list(SUBQUESTION_PATTERN.finditer(body))
    if not matches:
        cleaned = _clean_question(body)
        return _split_compound_question(cleaned) if cleaned else []

    parts = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        part_text = body[start:end].strip()
        cleaned = _clean_question(part_text)
        if cleaned:
            parts.extend(_split_compound_question(cleaned))
    return parts

def _clean_question(text: str) -> str:
    cleaned = re.sub(r"\[\d+\]", " ", text)
    cleaned = INLINE_ENUMERATION_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\b(?:also\s+)?(?:explain|discuss|describe|state|write)\s+with\s+example\.?$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:\n\t")
    return cleaned

def _split_compound_question(text: str) -> list[str]:
    pieces = [piece.strip() for piece in COMPOUND_QUESTION_PATTERN.split(text) if piece.strip()]
    if not pieces:
        return [text]

    resolved = []
    for piece in pieces:
        if resolved and FOLLOW_UP_START_PATTERN.match(piece):
            resolved[-1] = f"{resolved[-1]} {piece}"
        else:
            resolved.append(piece)

    return resolved

def _looks_like_question(text: str) -> bool:
    if len(text) < 20:
        return False

    lowered = text.lower()
    if any(
        phrase in lowered
        for phrase in (
            "answer q",
            "neat diagrams",
            "figures to the right side",
            "assume suitable data",
            "instructions to the candidates",
        )
    ):
        return False

    alpha_count = sum(char.isalpha() for char in text)
    if alpha_count < 12:
        return False

    starts_like_question = lowered.startswith(QUESTION_START_WORDS)
    has_question_mark = "?" in text
    return starts_like_question or has_question_mark
