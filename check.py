import json, glob

files = glob.glob('scraped data/*_chunks.json')
lengths = []

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
        for chunk in data:
            text = chunk.get('document_text', '')
            tokens = int(len(text.split()) * 1.3)
            lengths.append(tokens)

if lengths:
    print(f"\n--- Chunk Token Distribution ---")
    print(f"Total chunks: {len(lengths)}")
    print(f"Min tokens: {min(lengths)} | Max tokens: {max(lengths)} | Avg tokens: {sum(lengths)/len(lengths):.0f}\n")
    
    bins = [0, 250, 500, 1000, 2000, 4000, 10000]
    for i in range(len(bins)-1):
        low, high = bins[i], bins[i+1]
        count = sum(1 for x in lengths if low <= x < high)
        print(f"[{low:4d} - {high:<4d} tokens]: {'█' * (count // 2)} ({count} chunks)")
    
    huge_chunks = sum(1 for x in lengths if x >= 10000)
    print(f"[ > 10000    tokens]: {'█' * (huge_chunks // 2)} ({huge_chunks} chunks)")
