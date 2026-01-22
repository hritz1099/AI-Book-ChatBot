from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(text, max_length=1000):
    import re
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)  # Fix hyphenated words across lines
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'["""]', '"', text)  # Normalize quotes
    text = re.sub(r"[‘’']", "'", text)# Normalize apostrophes
    splitter = RecursiveCharacterTextSplitter(
         chunk_size=max_length,
          chunk_overlap=150,
          length_function=len
    )
    chunks=splitter.split_text(text)
    processed_chunks=[]
    for chunk in chunks:
        chunk=chunk.strip()
        if len(chunk)>50:
            processed_chunks.append(chunk)
    return processed_chunks
    # splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=max_length,
    #     chunk_overlap=100,
    #     length_function=len
    # )
    # chunks = splitter.split_text(text)
    # return chunks
