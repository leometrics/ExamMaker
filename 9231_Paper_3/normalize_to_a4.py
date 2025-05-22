import fitz  # PyMuPDF
import os

A4_WIDTH, A4_HEIGHT = 595, 842  # A4 size in points

def normalize_pdf_to_a4(input_path, output_path):
    doc = fitz.open(input_path)
    new_doc = fitz.open()

    for page in doc:
        # Create new A4-sized page
        new_page = new_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)

        # Calculate scale matrix to fit original content into A4
        scale_x = A4_WIDTH / page.rect.width
        scale_y = A4_HEIGHT / page.rect.height
        scale = min(scale_x, scale_y)

        # Calculate offset to center the content
        trans_x = (A4_WIDTH - page.rect.width * scale) / 2
        trans_y = (A4_HEIGHT - page.rect.height * scale) / 2

        # Create transformation matrix
        scale_matrix = fitz.Matrix(scale, scale)
        translate_matrix = fitz.Matrix(1, 0, 0, 1, trans_x, trans_y)
        matrix = scale_matrix * translate_matrix

        new_page.show_pdf_page(new_page.rect, doc, page.number, matrix)

    new_doc.save(output_path)
    new_doc.close()
    doc.close()

def batch_normalize(folder):
    for fname in os.listdir(folder):
        if fname.lower().endswith(".pdf"):
            input_path = os.path.join(folder, fname)
            output_path = input_path  # overwrite safely if you’ve backed up
            try:
                normalize_pdf_to_a4(input_path, output_path)
                print(f"✅ Normalized: {fname}")
            except Exception as e:
                print(f"❌ Failed: {fname} -> {e}")

if __name__ == "__main__":
    folder = "."  # current directory
    batch_normalize(folder)
