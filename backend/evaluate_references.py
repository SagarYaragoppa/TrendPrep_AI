import json
import os
from collections import Counter

from classifier import classify_question
from extractor import extract_questions_from_text, extract_relevant_text


def evaluate_reference_folder(folder: str) -> dict:
    syllabus_path = os.path.join(folder, "syllabus.txt")
    if not os.path.exists(syllabus_path):
        raise FileNotFoundError(f"Missing syllabus.txt in {folder}")

    syllabus = open(syllabus_path, "r", encoding="utf-8").read()
    pdf_files = [
        name for name in os.listdir(folder)
        if name.lower().endswith(".pdf")
        and "expected" not in name.lower()
        and "generated_" not in name.lower()
    ]

    route_counts = Counter()
    topic_counts = Counter()
    file_counts = {}

    for name in sorted(pdf_files):
        path = os.path.join(folder, name)
        text = extract_relevant_text(path, syllabus)
        questions = extract_questions_from_text(text)
        file_counts[name] = len(questions)

        for question in questions:
            result = classify_question(question, syllabus)
            route_counts[result["route"]] += 1
            topic_counts[result["topic"]] += 1

    return {
        "folder": folder,
        "files": file_counts,
        "routes": dict(route_counts),
        "topics": dict(topic_counts.most_common(10)),
        "total_questions": sum(file_counts.values()),
    }


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(__file__))
    references_dir = os.path.join(project_root, "references")
    folders = [
        os.path.join(references_dir, name)
        for name in sorted(os.listdir(references_dir))
        if os.path.isdir(os.path.join(references_dir, name))
    ]

    results = [evaluate_reference_folder(folder) for folder in folders]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
