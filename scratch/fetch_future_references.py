"""Retain public FIA baseline drawings for the returning circuits."""
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent/'pdf_tools'))
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
URLS = {
    'portugal': 'https://www.fia.com/sites/default/files/doc_1_-_2021_portuguese_grand_prix_-_circuit_map_1.pdf',
    'turkey': 'https://www.fia.com/sites/default/files/doc_1_-_2021_turkish_grand_prix_-_circuit_map.pdf',
}
for tid, url in URLS.items():
    target = ROOT/f'circuit_maps_2026/fia_reference/{tid}_2021.pdf'
    if not target.exists():
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        target.write_bytes(urllib.request.urlopen(req, timeout=45).read())
    doc = pymupdf.open(target)
    doc[-1].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(ROOT/f'scratch/fia_review/{tid}_circuit.png')
    print(tid, len(doc), 'pages', flush=True)
