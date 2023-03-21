from .base import ExeHelper
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
import os


class ElfHelper(ExeHelper):
    def __init__(self, name: str):
        self.elf = ELFFile(open(name, 'rb'))

    def get_opcodes(self, func_name: str):
        for section in self.elf.iter_sections():
            if isinstance(section, SymbolTableSection):
                symbols = section.get_symbol_by_name(func_name)
                if symbols is not None and len(symbols) > 0:
                    symbol = symbols[0]
                    sec = self.elf.get_section(symbol['st_shndx'])
                    offset = sec['sh_offset'] + symbol['st_value']
                    if self.elf.get_machine_arch() == 'ARM':
                        offset &= 0xFFFFFFFE
                    self.elf.stream.seek(offset, os.SEEK_SET)
                    return self.elf.stream.read(symbol['st_size'])
