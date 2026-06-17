import json
import re
import sys
from pathlib import Path

import fitz  # pymupdf

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

class TeachingPackGenerator:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parent.parent

        self.pdf_dir = self.project_root / "offline_assets" / "pdfs"

        self.output_dir = (
            self.project_root
            / "app"
            / "data"
            / "curriculum"
            / "packs"
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_text(self, pdf_path):

        text = ""

        try:

            doc = fitz.open(pdf_path)

            for page in doc:
                text += page.get_text("text") + "\n"

            doc.close()

        except Exception as e:
            print(f"ERROR reading {pdf_path}: {e}")

        return text

    def build_pack_from_pdf(self, text, chapter_name):
        pack = {
            "chapter_name": chapter_name,
            "concepts": [],
            "exercise_questions": []
        }
        
        # Clean up invisible/control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)

        # Extract Exercise Questions
        for ex_match in re.finditer(r'EXERCISE\s+(\d+\.\d+)(.*?)(?=\n\s*(?:EXERCISE|Theorem|Example|Summary|\Z))', text, re.DOTALL | re.IGNORECASE):
            ex_num = ex_match.group(1)
            ex_body = ex_match.group(2)
            markers = list(re.finditer(r"(?:^|\n)\s*(\d+)\.\s*", ex_body))
            for idx, marker in enumerate(markers):
                q_start = marker.end()
                q_end = markers[idx+1].start() if idx + 1 < len(markers) else len(ex_body)
                q_num = marker.group(1)
                q_prompt = re.sub(r'\s+', ' ', ex_body[q_start:q_end].strip())
                pack["exercise_questions"].append({
                    "exercise_id": f"Ex_{ex_num}",
                    "question_number": q_num,
                    "question_text": q_prompt
                })

        # Extract Concepts from Headings
        concept_matches = list(re.finditer(r'\n\s*(\d+\.\d+)\s+([A-Z][^\n]{2,80})', text))
        
        if not concept_matches:
            paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30]
            pack["concepts"].append({
                "concept_id": "1_1",
                "concept_name": "General Concepts",
                "definition_text": re.sub(r'\s+', ' ', paragraphs[0]) if paragraphs else "",
                "source_paragraphs": paragraphs[:10],
                "formulas": [],
                "theorems": [],
                "properties": [],
                "examples": []
            })
        else:
            for i, match in enumerate(concept_matches):
                marker = match.group(1).strip()
                title = match.group(2).strip()
                
                if title.lower().startswith("exercise"):
                    continue
                    
                start_idx = match.start()
                end_idx = concept_matches[i+1].start() if i + 1 < len(concept_matches) else len(text)
                chunk = text[start_idx:end_idx]

                theorems = []
                for thm_match in re.finditer(r'(?:^|\n)\s*(Theorem\s+\d+\.\d+(?:[^\n]{0,50})?[:\.])\s*(.*?)(?=\n\s*(?:Proof|Remark|Example|EXERCISE|Let |We |Now |Thus |By |\Z))', chunk, re.DOTALL | re.IGNORECASE):
                    theorems.append(re.sub(r'\s+', ' ', thm_match.group(2)).strip())

                examples = []
                for ex_match in re.finditer(r'Example\s+\d+[\s:]*(.*?)\n\s*Solution[\s:]*(.*?)(?=\n\s*(?:Example|EXERCISE|Theorem|\Z))', chunk, re.DOTALL | re.IGNORECASE):
                    question = re.sub(r'\s+', ' ', ex_match.group(1)).strip()
                    solution = ex_match.group(2).strip()
                    examples.append({
                        "question": question,
                        "solution_text": solution
                    })
                    
                # Extract formulas loosely by looking for equations with equals signs
                formulas = []
                for f_match in re.finditer(r'\n\s*([a-zA-Z0-9_\(\)\s\+\-\*\/]+=[a-zA-Z0-9_\(\)\s\+\-\*\/]+)\s*\n', chunk):
                    f_text = f_match.group(1).strip()
                    if len(f_text) > 4 and f_text not in formulas:
                        formulas.append(f_text)

                paragraphs = [p.strip() for p in chunk.split('\n\n') if len(p.strip()) > 30]

                pack["concepts"].append({
                    "concept_id": marker.replace('.', '_'),
                    "concept_name": f"{marker} {title}",
                    "definition_text": re.sub(r'\s+', ' ', paragraphs[0]) if paragraphs else "",
                    "source_paragraphs": paragraphs[:5],
                    "formulas": formulas,
                    "theorems": theorems,
                    "properties": [],
                    "examples": examples
                })

        return pack

    def process_pdf(self, pdf_path):

        chapter_name = pdf_path.stem.replace('_', ' ').title()

        print(f"\nProcessing: {chapter_name}")

        text = self.extract_text(pdf_path)

        if not text:
            print("No text extracted.")
            return

        print("Generating pack from PDF...")
        pack = self.build_pack_from_pdf(text, chapter_name)

        if not pack:
            print("Failed to generate pack.")
            return

        output_file = (
            self.output_dir
            / f"{pdf_path.stem}.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                pack,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(
            f"Saved: {output_file}"
        )

        print(
            f"Concepts Found: {len(pack.get('concepts', []))}"
        )

    def run(self):

        print("=================================")
        print("GENERATING TEACHING PACKS")
        print("=================================")

        if not self.pdf_dir.exists():

            print(
                f"PDF directory not found: {self.pdf_dir}"
            )
            return

        pdfs = list(
            self.pdf_dir.rglob("*.pdf")
        )

        print(
            f"PDF files found: {len(pdfs)}"
        )

        for pdf in pdfs:
            self.process_pdf(pdf)

        print("\nDONE")


if __name__ == "__main__":

    generator = TeachingPackGenerator()

    generator.run()