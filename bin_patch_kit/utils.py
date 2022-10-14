import re


def find_empty_space(name_or_buf, min_size=0x100, align=0x10):
    assert align & 1 == 0

    if isinstance(name_or_buf, str):
        buf = open(name_or_buf, 'rb').read()
    else:
        buf = name_or_buf

    spaces = []
    for m in re.finditer(b'\x00{%d,}' % min_size, buf):
        pos = (m.start() + align - 1) & (-align)
        size = (m.end() - pos) & (-align)
        spaces.append((pos, size))
    spaces.sort(key=lambda x: x[1], reverse=True)
    return spaces
