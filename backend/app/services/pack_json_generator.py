import json
import os
import glob
import re
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

class PackJsonGenerator:
    def __init__(self, pdf_dir_path: str):
        self.pdf_dir_path = Path(pdf_dir_path)
        # Define curriculum paths for scalability
        self.curriculum_dir = Path(__file__).resolve().parents[2] / "data" / "curriculum"
        self.output_dir = self.curriculum_dir / "packs"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_all_pdfs(self):
        """Finds all PDFs in the given directory."""
        pdf_files = glob.glob(str(self.pdf_dir_path / "*.pdf"))
        return pdf_files

    def extract_text(self, pdf_path):
        """Extracts raw text from a PDF using PyMuPDF and cleans headers/footers."""
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is not installed. Run `pip install PyMuPDF`.")
        
        doc = fitz.open(pdf_path)
        text = ""
        chapter_name_upper = Path(pdf_path).stem.replace('_', ' ').upper()
        for page in doc:
            page_text = page.get_text()
            lines = page_text.split('\n')
            cleaned_lines = []
            for line in lines:
                sline = line.strip()
                if not sline:
                    continue
                # Skip isolated page numbers
                if sline.isdigit():
                    continue
                # Skip reprint info
                if re.search(r'Reprint\s*\d{4}-\d{2,4}', sline, re.IGNORECASE):
                    continue
                if sline == "Rationalised 2023-24":
                    continue
                # Skip chapter names in headers
                if sline.upper() == chapter_name_upper or sline.upper() in ["REAL NUMBERS", "POLYNOMIALS", "MATHEMATICS"]:
                    continue
                cleaned_lines.append(line)
            text += "\n".join(cleaned_lines) + "\n"
        return text

    def extract_figures(self, pdf_path: str, file_stem: str) -> dict:
        """Problem #3 Fix: Actively crops and extracts figure images from the PDF using PyMuPDF."""
        extracted_paths = {}
        if not fitz:
            return extracted_paths
            
        figures_dir = self.output_dir / "figures" / file_stem
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_instances = page.search_for("Fig.")
                for rect in text_instances:
                    nearby_text = page.get_textbox(fitz.Rect(max(0, rect.x0 - 50), max(0, rect.y0 - 20), min(page.rect.width, rect.x1 + 100), min(page.rect.height, rect.y1 + 20)))
                    match = re.search(r'(Fig\.\s*\d+\.\d+)', nearby_text, re.IGNORECASE)
                    if match:
                        fig_num_raw = match.group(1)
                        safe_name = fig_num_raw.replace('.', '_').replace(' ', '').lower()
                        asset_path = figures_dir / f"{safe_name}.png"
                        
                        if not asset_path.exists():
                            crop_rect = fitz.Rect(max(0, rect.x0 - 250), max(0, rect.y0 - 300), min(page.rect.width, rect.x1 + 250), min(page.rect.height, rect.y1))
                            pix = page.get_pixmap(clip=crop_rect, matrix=fitz.Matrix(2, 2))
                            pix.save(str(asset_path))
                            
                        extracted_paths[fig_num_raw] = str(asset_path.relative_to(self.curriculum_dir))
        except Exception as e:
            print(f"Figure extraction failed for {file_stem}: {e}")
            
        return extracted_paths

    def parse_chapter_content(self, text, filename, figure_paths=None):
        """Uses rule-based heuristics to extract factual components from NCERT text."""
        # Clean text
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
        # 1. Extract Chapter Title
        title_match = re.search(r'^\s*([A-Z][A-Z\s]+)\s*\n', text)
        chapter_title = title_match.group(1).strip() if title_match else Path(filename).stem.replace('_', ' ').title()
        
        file_stem = Path(filename).stem
        
        # Problem #1 & #6 Fix: Strict regex to catch ONLY genuine section headers
        concept_matches = list(re.finditer(r'\n\s*(\d+\.\d+)\s+([A-Z][^\n]{2,80})', text))
        chunks = []
        if not concept_matches:
            chunks.append({
                "concept_id": f"{file_stem}_01",
                "concept_name": "General Concepts",
                "text_chunk": text
            })
        else:
            for i, match in enumerate(concept_matches):
                marker = match.group(1).strip().title()
                title = match.group(2).strip() if match.group(2) else ""
                concept_name_raw = title
                if concept_name_raw.lower().startswith("exercise"):
                    continue
                start_idx = match.start()
                end_idx = concept_matches[i+1].start() if i + 1 < len(concept_matches) else len(text)
                chunks.append({
                    "concept_id": f"{file_stem}_{i+1:02d}",
                    "concept_name": f"{marker} {concept_name_raw}".strip(),
                    "text_chunk": text[start_idx:end_idx]
                })

        def get_diagram_metadata(chunk_text: str) -> dict:
            """Problem #5 Fix: More robust heuristic to extract diagram data for rendering."""
            lower_text = chunk_text.lower()
            # Problem #4 Fix: Prepare explicit fields for a dedicated PDF Figure Extractor module
            metadata = {"diagram_type": "general_board", "diagram_data": {}, "figure_reference": None, "figure_asset_path": None}
            
            fig_match = re.search(r'(Fig\.\s*\d+\.\d+)', chunk_text, re.IGNORECASE)
            search_area = chunk_text
            if fig_match:
                start_pos = max(0, fig_match.start() - 500)
                end_pos = min(len(chunk_text), fig_match.end() + 500)
                search_area = chunk_text[start_pos:end_pos]
                ref_raw = fig_match.group(1)
                metadata["figure_reference"] = ref_raw
                
                # Problem #3 Fix: Tie actual extracted image assets into the pack
                if figure_paths:
                    norm_ref = re.sub(r'\s+', '', ref_raw.lower())
                    for k, v in figure_paths.items():
                        if re.sub(r'\s+', '', k.lower()) == norm_ref:
                            metadata["figure_asset_path"] = str(v).replace('\\', '/')
                            break

            if "triangle" in lower_text:
                metadata["diagram_type"] = "triangle"
                tri_match = re.search(r'(?:triangle|Δ)\s*([A-Z]{3})', search_area)
                if tri_match:
                    metadata["diagram_data"]["vertices"] = list(tri_match.group(1))

            elif "circle" in lower_text:
                metadata["diagram_type"] = "circle"
                circ_match = re.search(r'circle with centre\s+([A-Z])', search_area, re.IGNORECASE)
                if circ_match:
                    metadata["diagram_data"]["center"] = circ_match.group(1)
                else:
                    metadata["diagram_data"]["center"] = "O"

            elif "coordinate" in lower_text or "graph" in lower_text:
                metadata["diagram_type"] = "coordinate_plane"
                points = {}
                for p_match in re.finditer(r'\b([A-Z])\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)', search_area):
                    try:
                        points[p_match.group(1)] = [float(p_match.group(2)), float(p_match.group(3))]
                    except ValueError:
                        continue
                if points:
                    metadata["diagram_data"]["points"] = points

            elif "number line" in lower_text:
                metadata["diagram_type"] = "number_line"
                
            return metadata

        structured_concepts = []
        for i, chunk_data in enumerate(chunks):
            chunk = chunk_data["text_chunk"]
            
            theorems = []
            for match in re.finditer(r'(?:^|\n)\s*(Theorem\s+\d+\.\d+(?:[^\n]{0,50})?[:\.])\s*(.*?)(?=\n\s*(?:Proof|Remark|Example|EXERCISE|Let |We |Now |Thus |By |\Z))', chunk, re.DOTALL | re.IGNORECASE):
                statement = re.sub(r'\s+', ' ', match.group(2)).strip()
                
                # Problem #2 Fix: Extract proof structure sequentially
                proof_steps = []
                thm_end = match.end()
                next_marker = re.search(r'\n\s*(?:Theorem|Example|EXERCISE|\Z)', chunk[thm_end:], re.IGNORECASE)
                limit = next_marker.start() if next_marker else len(chunk) - thm_end
                proof_area = chunk[thm_end:thm_end+limit]
                
                proof_match = re.search(r'(?:^|\n)\s*Proof\s*:(.*?)(?=\n\s*(?:Remark|Example|EXERCISE|Theorem|\Z))', proof_area, re.DOTALL | re.IGNORECASE)
                if proof_match:
                    proof_text = proof_match.group(1).strip()
                    proof_steps = [s.strip() for s in proof_text.split('\n') if s.strip()]
                    
                theorems.append({
                    "statement": statement,
                    "proof_steps": proof_steps
                })
                
            # Problem #4 Fix: Capture full worked examples without truncation.
            worked_examples = []
            for match in re.finditer(r'Example\s+\d+[\s:]*(.*?)\n\s*Solution[\s:]*(.*?)(?=\n\s*(?:Example|EXERCISE|Theorem|\Z))', chunk, re.DOTALL | re.IGNORECASE):
                question = re.sub(r'\s+', ' ', match.group(1)).strip()
                solution_text = match.group(2).strip()
                steps = [s.strip() for s in solution_text.split('\n') if s.strip()]
                worked_examples.append({
                    "question": question,
                    "solution_steps": steps,
                    "final_answer": steps[-1] if steps else ""
                })
            
            exercises = []
            for ex_match in re.finditer(r'EXERCISE\s+(\d+\.\d+)(.*?)(?=\n\s*(?:EXERCISE|Theorem|Example|\Z))', chunk, re.DOTALL | re.IGNORECASE):
                ex_num = ex_match.group(1)
                ex_body = ex_match.group(2)
                
                markers = list(re.finditer(r"(?:^|\n)\s*(\d+)\.\s*", ex_body))
                for idx, marker in enumerate(markers):
                    q_start = marker.end()
                    q_end = markers[idx+1].start() if idx + 1 < len(markers) else len(ex_body)
                    q_num = marker.group(1)
                    q_prompt = re.sub(r'\s+', ' ', ex_body[q_start:q_end].strip())
                    
                    sub_markers = list(re.finditer(r"\(\s*(i{1,3}|iv|v|vi{0,3}|ix|x|[a-z])\s*\)", q_prompt, flags=re.IGNORECASE))
                    if sub_markers:
                        stem = q_prompt[:sub_markers[0].start()].strip(" :-")
                        for s_idx, s_marker in enumerate(sub_markers):
                            s_start = s_marker.end()
                            s_end = sub_markers[s_idx+1].start() if s_idx + 1 < len(sub_markers) else len(q_prompt)
                            sub_roman = s_marker.group(1).lower()
                            sub_text = q_prompt[s_start:s_end].strip(" .;:")
                            if sub_text:
                                full_prompt = f"{stem} ({sub_roman}) {sub_text}" if stem else f"({sub_roman}) {sub_text}"
                                exercises.append({
                                    "exercise": f"Exercise {ex_num}",
                                    "number": f"{q_num}({sub_roman})",
                                    "prompt": full_prompt
                                })
                    elif len(q_prompt) > 5:
                        exercises.append({
                            "exercise": f"Exercise {ex_num}",
                            "number": q_num,
                            "prompt": q_prompt
                        })

            depends_on = chunks[i-1]["concept_id"] if i > 0 else None
            next_concept = chunks[i+1]["concept_id"] if i + 1 < len(chunks) else None

            # Problem #2 Fix: Store discrete "board_templates" for EVERY example and theorem
            board_templates = []
            for t_idx, thm in enumerate(theorems):
                board_templates.append({
                    "type": "theorem",
                    "id": f"thm_{t_idx+1}",
                    "steps": [
                        {"step": 1, "board_text": f"Theorem: {chunk_data['concept_name']}"},
                        {"step": 2, "board_text": thm['statement']}
                    ]
                })
                # Fix: Keep all proof steps
                for p_idx, p_step in enumerate(thm['proof_steps']):
                    board_templates[-1]["steps"].append({"step": p_idx + 3, "board_text": f"Proof: {p_step}"})
                
            for e_idx, ex in enumerate(worked_examples):
                steps = [{"step": 1, "board_text": f"Problem: {ex['question']}"}]
                # Fix: Keep all solution steps
                for s_idx, sol_step in enumerate(ex["solution_steps"]):
                    steps.append({"step": s_idx + 2, "board_text": sol_step})
                board_templates.append({
                    "type": "example",
                    "id": f"ex_{e_idx+1}",
                    "steps": steps
                })

            if not board_templates:
                board_templates.append({
                    "type": "concept",
                    "id": "concept_1",
                    "steps": [{"step": 1, "board_text": f"Topic: {chunk_data['concept_name']}"}]
                })

            structured_concepts.append({
                "concept_id": chunk_data["concept_id"],
                "concept_name": chunk_data["concept_name"],
                
                "depends_on": depends_on,
                "next_concept": next_concept,
                
                "diagram_metadata": get_diagram_metadata(chunk),
                "theorems": theorems,
                "worked_examples": worked_examples,
                
                "exercises": exercises,
                "board_templates": board_templates
            })

        figures = []
        for match in re.finditer(r'(Fig\.\s*\d+\.\d+)', text, re.IGNORECASE):
            fig_ref = match.group(1).strip()
            if fig_ref not in figures:
                figures.append(fig_ref)

        summary_match = re.search(r'\b(?:Summary|What you have learnt)\b\s*\n(.*?)(?=\Z|Answers)', text, re.DOTALL | re.IGNORECASE)
        summary_text = re.sub(r'\s+', ' ', summary_match.group(1)).strip()[:1200] if summary_match else f"Core mathematical principles of {chapter_title}."

        return {
            "chapter_name": chapter_title,
            "concepts": structured_concepts,
            "figures": figures,
            "summary": summary_text
        }

    def generate_dynamic_packs(self):
        """Loops through all PDFs and generates dynamic, AI-free JSON packs."""
        pdf_files = self.get_all_pdfs()
        if not pdf_files:
            print(f"No PDFs found in {self.pdf_dir_path}")
            return

        for pdf_file in pdf_files:
            print(f"Processing dynamically: {pdf_file}")
            try:
                text = self.extract_text(pdf_file)
            except Exception as e:
                print(f"Failed to read {pdf_file}: {e}")
                continue

            parsed_data = self.parse_chapter_content(text, pdf_file)
            file_stem = Path(pdf_file).stem
            
            # Phase 3 Fix: Execute PyMuPDF figure extraction
            figure_paths = self.extract_figures(pdf_file, file_stem)
            parsed_data = self.parse_chapter_content(text, pdf_file, figure_paths)
            
            output_file = self.output_dir / f"{file_stem}_pack.json"
            # Issue 1 Fix: Dump as Dictionary, not Array ([pack_data] -> parsed_data)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)

            print(f"Success! Dynamic pack generated at: {output_file}")

if __name__ == "__main__":
    # Matches the exact local path provided in the prompt
    PDF_DIRECTORY = r"C:\Users\mites\mathverse\backend\offline_assets\pdfs\std_10"
    generator = PackJsonGenerator(PDF_DIRECTORY)
    generator.generate_dynamic_packs()