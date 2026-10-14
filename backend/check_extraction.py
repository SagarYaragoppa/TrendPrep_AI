import os
from backend.extractor import extract_text, extract_questions_from_text

folder = r"c:\Users\sagar\Desktop\project\my_error"

if not os.path.exists(folder):
    print("Folder not found ❌")
    exit()

pdfs = [f for f in os.listdir(folder) if f.endswith(".pdf") and "PATTERN" in f]

print(f"Found {len(pdfs)} PDF files")

for p in pdfs:
    try:
        text = extract_text(os.path.join(folder, p))
        qs = extract_questions_from_text(text)

        if not qs:
            print(f"{p}: No questions extracted ⚠️")
        else:
            print(f"{p}: extracted {len(qs)} questions.")

    except Exception as e:
        print(f"{p}: ERROR - {e}")