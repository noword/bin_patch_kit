import keystone
import capstone
from enum import Enum
import os


class ARCH(Enum):
    ARM = 0
    ARM_THUMB = 1
    ARM64 = 2
    X86 = 3
    X86_64 = 4


class ArchMode:
    KS_ARCH_MODE = {
        ARCH.ARM: (keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM),
        ARCH.ARM_THUMB: (keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB),
        ARCH.ARM64: (keystone.KS_ARCH_ARM64, keystone.KS_MODE_LITTLE_ENDIAN),
        ARCH.X86: (keystone.KS_ARCH_X86, keystone.KS_MODE_32),
        ARCH.X86_64: (keystone.KS_ARCH_X86, keystone.KS_MODE_64)
    }

    CS_ARCH_MODE = {
        ARCH.ARM: (capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM),
        ARCH.ARM_THUMB: (capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB),
        ARCH.ARM64: (capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN),
        ARCH.X86: (capstone.CS_ARCH_X86, capstone.CS_MODE_32),
        ARCH.X86_64: (capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    }

    def __init__(self, arch: ARCH):
        self.arch = arch

    @property
    def ks_arch_mode(self):
        return self.KS_ARCH_MODE[self.arch]

    @property
    def cs_arch_mode(self):
        return self.CS_ARCH_MODE[self.arch]


class Patcher:
    def __init__(self, io, base: int, arch_mode: ArchMode):
        self._io = io
        self._base = base
        self._arch_mode = arch_mode
        self._assembler = keystone.Ks(*arch_mode.ks_arch_mode)
        self._disassembler = capstone.Cs(*arch_mode.cs_arch_mode)

    # 以下 address 参数，均为不含 base 的，以 rom 为准的绝对地址
    def seek(self, address):
        if address:
            self._io.seek(address, os.SEEK_SET)
        return self._io.tell()

    def assemble(self, asm, address=None):
        # https://www.keystone-engine.org/docs/tutorial.html
        address = self.seek(address)
        encoding, count = self._assembler.asm(asm, self._base + address)
        # print(f'{self._base + address:08x} {bytes(encoding).hex()}\t{asm}')
        self._io.write(bytes(encoding))
        return len(encoding)

    def diassemble(self, address=None):
        # https://www.capstone-engine.org/lang_python.html
        address = self.seek(address)
        buf = self._io.read(64)
        result = next(self._disassembler.disasm(buf, self._base + address))
        self._io.seek(-64 + result.size, os.SEEK_CUR)
        return result

    def get_min_opcodes_len(self, address, min_size):
        addr = address
        while addr - address < min_size:
            r = self.diassemble(addr)
            addr += max(r.size, 1)
        return addr - address

    def push_all_regs(self, address=None):
        raise NotImplementedError

    def pop_all_regs(self, address=None):
        raise NotImplementedError

    def jump_patch(self, dst_address, address=None):
        raise NotImplementedError

    def call_patch(self, dst_address, address=None):
        raise NotImplementedError

    def nop_patch(self, size, address=None):
        raise NotImplementedError

    def _fix_opstr(self, instr, src_address, dst_address):
        return self.assemble(instr, dst_address)

    def relocate_opcodes(self, size, src_address, address=None):
        if address is None:
            address = self._io.tell()

        src_addr = src_address
        addr = address
        while src_addr - src_address < size:
            r = self.diassemble(src_addr)
            if r.size == 0:
                break
            addr += self._fix_opstr(f'{r.mnemonic} {r.op_str}', src_addr, addr)
            src_addr += r.size

        return addr - address

    def set_hooker(self, target_address: int, empty_address: int, function_codes: bytes):
        '''
            target                          empty space
            +----------------------+        +--------------------------------------------------------+
            | jmp empty            | ---->  | push all regs        |        function                 |
            | ...                  | <---+  | call hook function   | -----> +----------------------+ |
            |                      |     |  | pop all regs         | <---+  | ...                  | |
            |                      |     |  | run old instructions |     |  |                      | |
            |                      |     +- | jmp back             |     +- |                      | |
            |                      |        |                      |        +----------------------+ |
            +----------------------+        +--------------------------------------------------------+
        '''
        raise NotImplementedError


class ExeHelper:
    def get_physical_address(self, func_name: str):
        raise NotImplementedError

    def get_size(self, func_name: str):
        raise NotImplementedError

    def get_opcodes(self, func_name: str):
        raise NotImplementedError
