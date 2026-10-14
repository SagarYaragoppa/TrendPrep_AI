import os

from classifier import classify_question
from deduplicator import add_question, format_source_label
from document_generator import generate_pdf
from extractor import extract_questions_from_text, extract_relevant_text


def build_outputs_for_folder(folder: str) -> tuple[str, str]:
    syllabus_path = os.path.join(folder, "syllabus.txt")
    syllabus = open(syllabus_path, "r", encoding="utf-8").read()

    organized = {}
    pdf_files = [
        name for name in os.listdir(folder)
        if name.lower().endswith(".pdf")
        and "expected" not in name.lower()
        and "generated_" not in name.lower()
    ]

    for name in sorted(pdf_files):
        path = os.path.join(folder, name)
        text = extract_relevant_text(path, syllabus)
        questions = extract_questions_from_text(text)
        source = format_source_label(name)

        for question in questions:
            result = classify_question(question, syllabus)
            topic = result["topic"]
            subtopic = result["subtopic"]
            if result.get("route") == "review":
                topic = "Appendix - Needs Review"
                subtopic = f"{result.get('confidence', 'low').title()} Confidence"
            add_question(question, source, topic, subtopic, organized)

    clean = {
        topic: subtopics
        for topic, subtopics in organized.items()
        if not topic.startswith("Appendix") and not topic.startswith("__")
    }

    clean_path = os.path.join(folder, "generated_clean_output.pdf")
    full_path = os.path.join(folder, "generated_full_output.pdf")
    with open(clean_path, "wb") as handle:
        handle.write(generate_pdf(clean).getvalue())
    with open(full_path, "wb") as handle:
        handle.write(generate_pdf(organized).getvalue())

    return clean_path, full_path


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(__file__))
    references_dir = os.path.join(project_root, "references")
    folders = [
        os.path.join(references_dir, name)
        for name in sorted(os.listdir(references_dir))
        if os.path.isdir(os.path.join(references_dir, name))
    ]

    for folder in folders:
        clean_path, full_path = build_outputs_for_folder(folder)
        print(clean_path)
        print(full_path)


if __name__ == "__main__":
    main()
