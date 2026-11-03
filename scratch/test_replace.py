import pathlib

p = pathlib.Path('data/test_direct_write.json')
p.write_text('{"test": 1}', encoding='utf-8')

f = open(p, 'r', encoding='utf-8')
try:
    p.write_text('{"test": 2}', encoding='utf-8')
    print('Direct write_text SUCCEEDED while file is open!')
except Exception as e:
    print('Direct write_text FAILED:', type(e), e)
finally:
    f.close()
    if p.exists(): p.unlink()
