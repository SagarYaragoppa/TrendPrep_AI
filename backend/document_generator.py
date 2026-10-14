from fpdf import FPDF
import io
import re

try:
    from deduplicator import sort_sources
except ImportError:
    from backend.deduplicator import sort_sources

def generate_pdf(organized_questions: dict) -> io.BytesIO:
    """Generate a highly structured PDF similar to user expectation."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="Organized Question Papers (PYQs)", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)
    
    for topic, subtopics in _sort_topics(organized_questions):
        pdf.set_font("Helvetica", style="B", size=14)
        clean_topic = topic.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, txt=clean_topic, new_x="LMARGIN", new_y="NEXT", align='L')
        
        for subtopic, questions_list in _sort_subtopics(subtopics):
            if not questions_list:
                continue
            pdf.set_font("Helvetica", style="B", size=12)
            clean_subtopic = subtopic.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 8, txt="  " + clean_subtopic, new_x="LMARGIN", new_y="NEXT", align='L')
            
            sorted_questions = sorted(
                questions_list,
                key=lambda item: (-len(item["sources"]), item["main_question"].lower()),
            )

            for idx, q_dict in enumerate(sorted_questions, 1):
                # Main Question
                pdf.set_font("Helvetica", style="B", size=11)
                main_q = q_dict["main_question"].encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 6, txt=f"    Q{idx}. {main_q}", new_x="LMARGIN", new_y="NEXT")
                
                # Sources Info
                pdf.set_font("Helvetica", style="I", size=10)
                sorted_sources = sort_sources(q_dict["sources"])
                sources_str = ", ".join(sorted_sources)
                pdf.multi_cell(
                    0,
                    6,
                    txt=f"    (PYQ - {sources_str}) - {len(sorted_sources)}T",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                
                # Variants
                if len(q_dict["variants"]) > 1:
                    pdf.set_font("Helvetica", style="", size=10)
                    pdf.multi_cell(0, 5, txt="    Merged from:", new_x="LMARGIN", new_y="NEXT")
                    for v in q_dict["variants"]:
                        clean_v = v.encode('latin-1', 'replace').decode('latin-1')
                        pdf.multi_cell(0, 5, txt=f"      - {clean_v}", new_x="LMARGIN", new_y="NEXT")
                
                pdf.ln(3)

    pdf_bytes = pdf.output()
    return io.BytesIO(bytes(pdf_bytes))

def _sort_topics(organized_questions: dict) -> list[tuple[str, dict]]:
    visible_items = [(topic, subtopics) for topic, subtopics in organized_questions.items() if not topic.startswith("__")]
    return sorted(visible_items, key=lambda item: _number_key(item[0]))

def _sort_subtopics(subtopics: dict) -> list[tuple[str, list]]:
    return sorted(subtopics.items(), key=lambda item: _number_key(item[0]))

def _number_key(text: str) -> tuple[int, int, str]:
    if text.lower().startswith("appendix"):
        return (9999, 9999, text.lower())

    unit_match = re.search(r"unit\s+([ivxlcdm]+)", text, flags=re.I)
    if unit_match:
        return (_roman_to_int(unit_match.group(1)), 0, text.lower())

    decimal_match = re.match(r"\s*(\d+)(?:\.(\d+))?", text)
    if decimal_match:
        major = int(decimal_match.group(1))
        minor = int(decimal_match.group(2) or 0)
        return (999, major * 100 + minor, text.lower())

    return (999, 999, text.lower())

def _roman_to_int(value: str) -> int:
    numerals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    previous = 0
    for char in reversed(value.lower()):
        current = numerals.get(char, 0)
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total
