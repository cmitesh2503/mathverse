import fitz  # PyMuPDF
import re
import os
import glob

def process_ncert_pdf(input_pdf_path, output_base_dir, grade, chapter_folder_name):
    print(f"\n⚙️ Processing: {os.path.basename(input_pdf_path)}")
    try:
        doc = fitz.open(input_pdf_path)
    except Exception as e:
        print(f"❌ Failed to open {input_pdf_path}: {e}")
        return

    categories = {
        "theory": [],
        "examples": [],
        "practice": []
    }
    
    current_mode = "theory" 
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        
        if re.search(r'EXERCISE\s+\d+\.\d+', text, re.IGNORECASE):
            current_mode = "practice"
        elif re.search(r'Example\s+\d+', text, re.IGNORECASE):
            current_mode = "examples"
        elif re.search(r'^\s*\d+\.\d+\s+[A-Z]', text, re.MULTILINE):
            current_mode = "theory"
            
        categories[current_mode].append(page_num)

    chapter_dir = os.path.join(output_base_dir, grade, chapter_folder_name)
    os.makedirs(chapter_dir, exist_ok=True)
    
    for category, page_numbers in categories.items():
        if not page_numbers:
            continue
            
        new_doc = fitz.open()
        for pno in page_numbers:
            new_doc.insert_pdf(doc, from_page=pno, to_page=pno)
            
        output_file = os.path.join(chapter_dir, f"{category}.pdf")
        new_doc.save(output_file)
        new_doc.close()
        print(f"  ✅ Saved {category}.pdf ({len(page_numbers)} pages)")
        
    doc.close()

def run_batch_split():
    # Dynamically find the backend root directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    
    # Build the exact absolute paths pointing to the app/data folder
    input_dir = os.path.join(backend_dir, "app", "data", "pdfs", "std_10")
    output_dir = os.path.join(backend_dir, "app", "data", "curriculum", "cbse")
    grade = "grade_10"
    
    print(f"🔍 Looking for PDFs in: {input_dir}")
    print(f"📁 Outputting to: {output_dir}")
    
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No PDFs found. Please check if files exist in the path above.")
        return

    print(f"🚀 Found {len(pdf_files)} chapters. Starting batch split...")
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        match = re.search(r'ch(\d+)', filename, re.IGNORECASE)
        if match:
            ch_num = match.group(1).zfill(2) 
            chapter_folder_name = f"ch_{ch_num}"
            process_ncert_pdf(pdf_path, output_dir, grade, chapter_folder_name)
        else:
            print(f"⚠️ Skipping {filename}: Could not extract 'chX' number.")

if __name__ == "__main__":
    run_batch_split()