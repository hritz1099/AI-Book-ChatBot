import PyPDF2
from bs4 import BeautifulSoup
import os

def read_file_from_path(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as file:
        if ext == ".pdf":
            return read_pdf(file)
        elif ext == ".txt":
            return read_txt(file)
        elif ext == ".html" or ext == ".htm":
            return read_html(file)
        else:
            return "Unsupported file type."

def read_pdf(file_obj):
    try:
        pdf_reader=PyPDF2.PdfReader(file_obj)
        text=""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text=page.extract_text()
            if page_num>0:
                text+=f"\n\n--- Page {page_num+1}- ---\n\n"
            text+=page_text
        import re
        text=re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        text = re.sub(r'\s+([.!?,:;])', r'\1', text)
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[‘’']", "'", text)
        return text
    except Exception as e:
        return f'Error reading PDF:{str(e)}'

    # pdf_reader = PyPDF2.PdfReader(file_obj)
    # text = ""
    # for page in pdf_reader.pages:
    #     text += page.extract_text()
    # return text

def read_txt(file_obj):
    return file_obj.read().decode("utf-8")

def read_html(file_obj):
    content = file_obj.read().decode("utf-8")
    soup = BeautifulSoup(content, "html.parser")
    return soup.get_text()
