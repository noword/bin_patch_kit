# Bin Patch Kit

## 为什么会有这个项目？

第一次汉化 GBA 游戏，需要注入自己的代码，不想苦哈哈的写汇编，所以写了这个东西。目前仅支持 ARM32，THUMB-2，THUMB-1 指令集的注入，理论上 NDS，3DS，PSV 等使用 ARM 指令集的 rom 也能用。注意：修复指令的功能并没有充分测试，使用时风险自负。

## 原理

```
target               empty space
+-----------+        +------------------------------------------+
| jmp empty | ---->  | push all regs        |        function   |
| ...       | <---+  | call hook function   | -----> +--------+ |
|           |     |  | pop all regs         | <---+  | ...    | |
|           |     |  | run old instructions |     |  |        | |
|           |     +- | jmp back             |     +- |        | |
|           |        |                      |        +--------+ |
+-----------+        +------------------------------------------+
```
由于所有寄存器入栈并作为参数传给了 ```function```，所以在用 C 写的 ```function``` 内可以任意读取和修改寄存器。

## 怎么用？

### 1. 写一个 C 程序

```c
// main.c
#include "registers.h"

// ...

__attribute__((target("arm"))) void hooker_0000xxxx(struct Registers *regs)
{
    *(char *)regs->r0 = 'X';
    regs->r1++;
    return;
}

__attribute__((target("thumb"))) void hooker_0000yyyy(struct Registers *regs)
{
    if (*(uint32_t *)regs->sp == 0x08001234)
    {
        regs->r3 = regs->r4;
    }
    return;
}
```

在 [devkitPro](https://github.com/devkitPro/installer/releases) 中编译。

> ### 注意点:
* Makefile 可以从 gba 的 examples 里面 copy 一个过来, 要在 CFLAG 里加上 -fno-builtin
* 如果是 hook 在 arm 指令上，函数前加 ``` __attribute__((target("arm")))``` 
* 如果是 hook 在 thumb 指令上，函数前加 ``` __attribute__((target("thumb")))```
* 函数内要调用的其他函数，必须是 ```inline``` 的，所以不能使用一些最基本的 libc 函数，如 memcpy, memset 等，需要自己实现。

### 2. 写一个 python 程序
```python
from bin_patch_kit import *

ELF = ElfHelper('build/main.o')

ROM_PATH = '../rom/XXX.gba'

JOBS = [
    {
        'arch': 'arm',
        'hooker': [{'address': 0x5b7c, 'func': 'hooker_0000xxxx'}],
    },
    {
        'arch': 'thumb',
        'hooker': [{'address': 0x2190, 'func': 'hooker_0000yyyy'}],
        'patch': [{'address': 0x186c, 'asm': 'mov r8, r8; mov r8, r8;'}, ]
    }
]

empty_address = 0x003919a0

for job in JOBS:
    if job['arch'] == 'arm':
        patcher = ArmPatcher(open(ROM_PATH, 'rb+'), base=0x08000000)
    elif job['arch'] == 'thumb':
        patcher = ThumbPatcher(open(ROM_PATH, 'rb+'), base=0x08000000)
    else:
        raise TypeError

    if 'hooker' in job:
        for h in job['hooker']:
            codes = ELF.get_opcodes(h['func'])
            size = patcher.set_hooker(target_address=h['address'],
                                      empty_address=empty_address,
                                      function_codes=codes)
            empty_address = (empty_address + size + 0xf) & 0xfffffff0

    if 'patch' in job:
        for p in job['patch']:
            patcher.assmble(p['asm'], p['address'])

    del patcher

assert empty_address < 0x00393000
```
> ### 注意点
* 注入的地址要用反编译工具确认地址下面的几个指令没有从其他地方跳转的情况出现
* python 依赖库：
  
  [keystone-engine](https://pypi.org/project/keystone-engine/)

  [capstone](https://pypi.org/project/capstone/)

  [pyelftools](https://pypi.org/project/pyelftools/)