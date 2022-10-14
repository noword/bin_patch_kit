from .base import ExeHelper
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
import os


class ElfHelper(ExeHelper):
    def __init__(self, name: str):
        self.elf = ELFFile(open(name, 'rb'))

    def get_physical_address(self, func_name: str):
        text_offset = offset = None
        for s in self.elf.iter_sections():
            if s.name == '.text':
                text_offset = s['sh_offset']
            elif isinstance(s, SymbolTableSection):
                for symbol in s.iter_symbols():
                    if symbol.name == func_name:
                        offset = symbol['st_value']
            if text_offset is not None and offset is not None:
                break

        assert text_offset is not None
        assert offset is not None

        if self.elf.get_machine_arch() == 'ARM':
            offset &= 0xFFFFFFFE

        return text_offset + offset

    def get_size(self, func_name: str):
        for s in self.elf.iter_sections():
            if isinstance(s, SymbolTableSection):
                for symbol in s.iter_symbols():
                    if symbol.name == func_name:
                        return symbol['st_size']

    def get_opcodes(self, func_name: str):
        offset = self.get_physical_address(func_name)
        size = self.get_size(func_name)
        self.elf.stream.seek(offset, os.SEEK_SET)
        return self.elf.stream.read(size)
