from pypdf import PdfReader
import sys

def main():
    reader = PdfReader("docs/ResQ-Graph_Sprint_Schedule.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    with open("sprint_schedule.txt", "w", encoding="utf-8") as f:
        f.write(text)
        
if __name__ == "__main__":
    main()
