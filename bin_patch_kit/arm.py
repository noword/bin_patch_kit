from .base import *
from struct import pack
import re


def SET_BIT0(addr):
    return addr | 1


def CLEAR_BIT0(addr):
    return addr & 0xFFFFFFFE


def TEST_BIT0(addr):
    return addr & 1


def TEST_ALIGN_4(addr):
    return addr & 3 == 0


def ALIGN_4(addre):
    return addre & 0xFFFFFFFC


def ALIGN_UP(size, align):
    return (size + align - 1) & ~(align - 1)


class ArmPatcher(Patcher):
    def __init__(self, io, base):
        super().__init__(io, base, ArchMode(ARCH.ARM))

    def nop_patch(self, size, address=None):
        length = 0
        for i in range(size):
            length += self.assemble('mov r0, r0', address)
        return length

    def push_all_regs(self, address=None):
        return self.assemble(
            'str sp, [sp, #-4];' 'sub sp, #4;' 'push {r0-r12, lr};' 'mrs r0, cpsr;' 'push {r0};', address
        )

    def pop_all_regs(self, address=None):
        return self.assemble('pop {r0};' 'msr cpsr, r0;' 'pop {r0-r12, lr};' 'add sp, #4;', address)

    def _in_range(self, addr1, addr2):
        return abs(addr1 - addr2) < 0x2000000

    def _get_jmp_patch_size(self, dst_address, address):
        return 4 if self._in_range(dst_address, address) else 8

    def jump_patch(self, dst_address, address=None):
        address = self.seek(address)
        length = 0
        if self._in_range(dst_address, address):
            # jump range is in 32M
            length = self.assemble(f'b #0x{self._base+dst_address:x}')
        else:
            length = self.assemble('ldr pc, [pc, #-4]')
            self._io.write(pack('<I', self._base + dst_address))
            length += 4
        return length

    def call_patch(self, dst_address, address=None):
        address = self.seek(address)
        length = 0
        if self._in_range(address, dst_address):
            length = self.assemble(f'bl #0x{self._base+dst_address:x}')
        else:
            length = self.assemble('add lr, pc, #4;' 'ldr pc, [pc, #-4];', address)
            self._io.write(pack('<I', self._base + dst_address))
            length += 4
        return length

    def set_hooker(self, target_address: int, empty_address: int, function_codes: bytes):
        size = self._get_jmp_patch_size(target_address, empty_address)

        self.push_all_regs(empty_address)
        self.assemble('mov r0, sp')
        call_addr = self._io.tell()
        self.call_patch(self._io.tell() + 0x10)  # we'll rewrite it later
        self.pop_all_regs()
        self.relocate_opcodes(size, target_address)
        self.jump_patch(target_address + size)

        func_addr = self._io.tell()
        self._io.write(function_codes)
        size = self._io.tell() - empty_address
        self.call_patch(func_addr, call_addr)

        self.jump_patch(empty_address, target_address)
        return size

    def set_function_hooker(self, target_address: int, empty_address: int, function_codes: bytes):
        size = self._get_jmp_patch_size(target_address, empty_address)
        self.push_all_regs(empty_address)
        self.assemble('mov r0, sp')
        call_addr = self._io.tell()
        self.call_patch(self._io.tell() + 0x10)  # we'll rewrite it later
        # print('%x' % self._io.tell())
        # if 'Thumb' in type(self).__name__:
        #     self.assemble(f'cbz r0, #0x{self._io.tell()+0x10:08x}')
        # else:
        self.assemble('cmp r0, 0')
        self.assemble(f'beq #0x{self._base+self._io.tell()+0x1c:08x}')
        self.pop_all_regs()
        self.assemble('mov pc, lr')
        self.pop_all_regs()
        self.relocate_opcodes(size, target_address)

        self.jump_patch(target_address + size)

        func_addr = self._io.tell()
        self._io.write(function_codes)
        size = self._io.tell() - empty_address
        self.call_patch(func_addr, call_addr)

        self.jump_patch(empty_address, target_address)
        return size

    PC_RE = re.compile(r'(.*,.*)pc(.*)')

    def __fix_pc(self, instr, src_address, dst_address):
        def find_empty_register(s):
            for r in [f'r{i}' for i in range(8)]:
                if r not in s:
                    return r

        length = 0
        if 'pop' not in instr:
            m = self.PC_RE.search(instr)
            if m:
                # fix instruction with pc
                header = m.group(1)
                tail = m.group(2)

                if self._arch_mode == ARCH.ARM_THUMB:
                    pc = CLEAR_BIT0(src_address) + 4
                    if '[' in instr:
                        pc = ALIGN_4(pc)
                else:
                    pc = src_address + 8

                reg = find_empty_register(instr)

                adjust1, adjust2 = (4, 6) if self._arch_mode == ARCH.ARM_THUMB else (8, 8)

                if self._arch_mode == ARCH.ARM_THUMB and TEST_ALIGN_4(dst_address):
                    length = self.nop_patch(1, dst_address)

                length += self.assemble(
                    f'push {{ {reg} }};'
                    f'ldr {reg}, [pc, #{adjust1}];'
                    f'{header}{reg}{tail};'
                    f'pop {{ {reg} }};'
                    f'b #0x{self._base+self._io.tell()+ adjust2:x};'
                )
                self._io.write(pack('I', self._base + pc))
                length += 4

        return length

    BRANCH_RE = re.compile(
        r'^((?:bl?x?(?:eq|ne|cs|hs|cc|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al)?)|cbz|cbnz)(?:\.w)? (.*)#([\dabcdefx]+)'
    )

    def __fix_branch(self, instr, src_address, dst_address):
        length = 0
        m = self.BRANCH_RE.search(instr)
        if m:
            cmd = m.group(1)
            reg = m.group(2)
            digitstr = m.group(3)
            addr = int(digitstr, 16)
            if cmd in ('bl', 'blx'):
                length = self.call_patch(addr, dst_address)
            elif cmd in ('b', 'bx'):
                length = self.jump_patch(addr, dst_address)
            elif cmd in ('cbz', 'cbnz'):
                adjust1, adjust2 = (4, 0xA) if self._arch_mode.arch == ARCH.ARM_THUMB else (8, 0xC)
                length = self.assemble(f'{cmd} {reg} #0x{self._base+dst_address+adjust1:08x}', dst_address)
                length += self.assemble(f'b #0x{self._base+dst_address+length+adjust2:08x}')
                length += self.jump_patch(addr - self._base)
            else:
                # conditional jmp
                adjust1, adjust2 = (4, 0xE) if self._arch_mode.arch == ARCH.ARM_THUMB else (8, 0xC)
                length = self.assemble(f'{cmd} #0x{self._base+dst_address+adjust1:08x}', dst_address)
                length += self.assemble(f'b #0x{self._base+dst_address+length+adjust2:08x}')
                length += self.jump_patch(addr - self._base)

        return length

    def _fix_opstr(self, instr, src_address, dst_address):
        length = self.__fix_pc(instr, src_address, dst_address)

        if length == 0:
            length = self.__fix_branch(instr, src_address, dst_address)

        if length == 0:
            length = self.assemble(instr, dst_address)

        return length


class Thumb2Patcher(ArmPatcher):
    # support 32bits thumb instructions
    def __init__(self, io, base):
        super(ArmPatcher, self).__init__(io, base, ArchMode(ARCH.ARM_THUMB))

    def _in_range(self, addr1, addr2):
        return abs(addr1 - addr2) < 0x1000000

    def nop_patch(self, size, address=None):
        length = 0
        for i in range(size):
            length += self.assemble('mov r8, r8', address)
        return length

    def jump_patch(self, dst_address, address=None):
        address = self.seek(address)
        length = 0
        if self._in_range(address, dst_address):
            length = self.assemble(f'b #0x{self._base+dst_address:x}')
        else:
            length = self.assemble(f'ldr.w pc, [pc, #{address&2:x}];')
            self._io.write(pack('<I', self._base + dst_address))
            length += 4
        return length

    def call_patch(self, dst_address, address=None):
        address = self.seek(address)
        length = 0
        if self._in_range(address, dst_address):
            length = self.assemble(f'bl #0x{self._base+dst_address:x}')
        else:
            align4 = address & 2
            length = self.assemble(f'add lr, pc, #{align4+9:x}')
            length += self.assemble(f'ldr.w pc, [pc, #{align4:x}]')
            self._io.write(pack('I', self._base + CLEAR_BIT0(dst_address)))
            length += 4
        return length


class ThumbPatcher(Thumb2Patcher):
    def _in_range(self, addr1, addr2):
        return abs(addr1 - addr2) < 0x800

    def push_all_regs(self, address=None):
        # return self.assemble('sub sp, 0x1c;'  # skip r8-r15
        #                      'push {r0-r7};'
        #                      'sub sp, 4;',  # skip cpsr
        #                      address)
        return self.assemble(
            'mov r12, r0;'
            'mov r0, sp; push {r0};'
            'mov r0, lr; push {r0};'
            'sub sp, 4;'  # skip r12
            'mov r0, r11; push {r0};'
            'mov r0, r10; push {r0};'
            'mov r0, r9; push {r0};'
            'mov r0, r8; push {r0};'
            'mov r0, r12;'
            'push {r0-r7};'
            'sub sp, 4;',  # skip cpsr
            address,
        )

    def pop_all_regs(self, address=None):
        return self.assemble(
            'add sp, 4;'  # skip cpsr
            'pop {r0-r7};'
            'mov r12, r0;'
            'pop {r0}; mov r8, r0;'
            'pop {r0}; mov r9, r0;'
            'pop {r0}; mov r10, r0;'
            'pop {r0}; mov r11, r0;'
            'add sp, 0x4;'
            'pop {r0}; mov lr, r0;'
            'pop {r0}; mov sp, r0;'
            'mov r0, r12;',
            address,
        )

    def _get_jmp_patch_size(self, dst_address, address):
        if self._in_range(dst_address, address):
            return 2
        elif dst_address & 2 == 0:
            return 0xC
        else:
            return 0xE

    def jump_patch(self, dst_address, address=None):
        address = self.seek(address)
        length = 0
        if self._in_range(address, dst_address):
            length = self.assemble(f'b #0x{self._base+dst_address:x}')
        else:
            length = self.assemble('push {r0, r1};' 'ldr r0, [pc, #4];' 'str r0, [sp, #4];' 'pop {r0, pc};')
            if not TEST_ALIGN_4(self._io.tell()):
                length += self.nop_patch(1)
            self._io.write(pack('I', self._base + SET_BIT0(dst_address)))
            length += 4
        return length

    def call_patch(self, dst_address, address=None):
        address = self.seek(address)
        length = 0
        if self._in_range(address, dst_address):
            length = self.assemble(f'bl #0x{self._base+dst_address:x}')
        else:
            length = self.assemble(
                'push {r0, r1};'
                'mov r0, pc;'
                'adds r0, #0xc;'
                'mov lr, r0;'
                'ldr r0, [pc, #4];'
                'str r0, [sp, #4];'
                'pop {r0, pc};'
            )
            if not TEST_ALIGN_4(self._io.tell()):
                length += self.nop_patch(1)
            self._io.write(pack('I', self._base + CLEAR_BIT0(dst_address)))
            length += 4
        return length
