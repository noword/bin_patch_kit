import re
from .elf import ElfHelper
from .arm import ArmPatcher, ThumbPatcher, ALIGN_UP

GBA_BASE = 0x08000000
NDS_BASE = 0x02000000


def patch_rom(rom_path: str, rom_base: int, code_path: str, empty_address: int, jobs: dict):
    '''
    jobs = [
        {
            'arch': str `arm/thumb`,
            'hooker': [ ['address': int `rom address (absolute address)`, 'func': str `function name in code` ], ... ]
            'patch':  [ ['address': int `rom address (absolute address)`, 'asm': str `asm codes` ], ... ]
        },
        ...
    ]
    '''

    elf = ElfHelper(code_path)
    for job in jobs:
        if job['arch'] == 'arm':
            patcher = ArmPatcher(open(rom_path, 'rb+'), base=rom_base)
        elif job['arch'] == 'thumb':
            patcher = ThumbPatcher(open(rom_path, 'rb+'), base=rom_base)
        else:
            raise TypeError(f"Not support architecture: {job['arch']}")

        if 'hooker' in job:
            for h in job['hooker']:
                codes = elf.get_opcodes(h['func'])
                size = patcher.set_hooker(target_address=h['address'],
                                          empty_address=empty_address,
                                          function_codes=codes)
                empty_address = ALIGN_UP(empty_address + size, 0x10)

        if 'patch' in job:
            for p in job['patch']:
                patcher.assemble(p['asm'], p['address'])

        del patcher


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
