import os
import json
from extractor import extract_text, extract_questions_from_text
from classifier import classify_question
from deduplicator import add_question, format_source_label

def test():
    pdf_path = r"c:\Users\sagar\Desktop\project\my_error\T.E ( 2019 PATTERN ) April 2022.pdf"
    syllabus = open(r"c:\Users\sagar\Desktop\project\my_error\syllabus.txt", "r", encoding="utf-8").read()
    
    print("Extracting text...")
    text = extract_text(pdf_path)
    questions = extract_questions_from_text(text)
    print(f"Extracted {len(questions)} questions.")
    
    organized_data = {}
    for i, q in enumerate(questions[:5]):
        print(f"\nQ: {q[:100]}...")
        classification = classify_question(q, syllabus)
        print(f"Classified as: {classification}")
        topic = classification.get("topic", "Unclassified")
        subtopic = classification.get("subtopic", "Unclassified")
        if topic != "Off Topic":
            add_question(q, format_source_label(os.path.basename(pdf_path)), topic, subtopic, organized_data)
        
    print("\nOrganized Data:", json.dumps(organized_data, indent=2))

if __name__ == "__main__":
    test()
