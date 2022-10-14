#ifndef __REGISTERS_H__
#define __REGISTERS_H__

#ifdef _MSC_VER
#include <windows.h>
typedef DWORD32 uint32_t;
typedef DWORD64 uint64_t;
#endif

#if defined(__linux__) || defined(__APPLE__) || defined(__MINGW32__) || defined(__GNUC__)
#include <unistd.h>
#include <stdint.h>
#endif

#pragma pack(push, 4)

struct XmmRegister
{
    union
    {
        uint64_t LowDWORD64;
        double Low;
    };
    union
    {
        uint64_t HighDWORD64;
        double High;
    };
};

struct Registers
{
#if defined(__arm__)
    // arm
    uint32_t cpsr;
    uint32_t r0;
    uint32_t r1;
    uint32_t r2;
    uint32_t r3;
    uint32_t r4;
    uint32_t r5;
    uint32_t r6;
    uint32_t r7;
    uint32_t r8;
    uint32_t r9;
    uint32_t r10;
    uint32_t r11;
    uint32_t r12;
    union
    {
        uint32_t r14;
        uint32_t lr;
    };
    union
    {
        uint32_t r13;
        uint32_t sp;
    };
#elif defined(__aarch64__)
    // arm 64
    uint64_t nzcv;
    uint64_t xzr; // for align purpose
    uint64_t x0;
    uint64_t x1;
    uint64_t x2;
    uint64_t x3;
    uint64_t x4;
    uint64_t x5;
    uint64_t x6;
    uint64_t x7;
    uint64_t x8;
    uint64_t x9;
    uint64_t x10;
    uint64_t x11;
    uint64_t x12;
    uint64_t x13;
    uint64_t x14;
    uint64_t x15;
    union
    {
        uint64_t x16;
        uint64_t ip0;
    };
    union
    {
        uint64_t x17;
        uint64_t ip1;
    };
    uint64_t x18;
    uint64_t x19;
    uint64_t x20;
    uint64_t x21;
    uint64_t x22;
    uint64_t x23;
    uint64_t x24;
    uint64_t x25;
    uint64_t x26;
    uint64_t x27;
    uint64_t x28;
    union
    {
        uint64_t x29;
        uint64_t fp;
    };
    union
    {
        uint64_t x30;
        uint64_t lr;
    };
    union
    {
        uint64_t x31;
        uint64_t sp;
    };
#elif defined(__amd64__) || defined(_M_AMD64)
    // x86_64
    XmmRegister xmm7;
    XmmRegister xmm6;
    XmmRegister xmm5;
    XmmRegister xmm4;
    XmmRegister xmm3;
    XmmRegister xmm2;
    XmmRegister xmm1;
    XmmRegister xmm0;
    uint64_t rflags;
    uint64_t r15;
    uint64_t r14;
    uint64_t r13;
    uint64_t r12;
    uint64_t r11;
    uint64_t r10;
    uint64_t r9;
    uint64_t r8;
    uint64_t rdi;
    uint64_t rsi;
    uint64_t rbp;
    uint64_t rbx;
    uint64_t rdx;
    uint64_t rcx;
    uint64_t rax;
    uint64_t rsp;
#else
    // x86
    XmmRegister xmm7;
    XmmRegister xmm6;
    XmmRegister xmm5;
    XmmRegister xmm4;
    XmmRegister xmm3;
    XmmRegister xmm2;
    XmmRegister xmm1;
    XmmRegister xmm0;
    uint32_t eflags;
    uint32_t edi;
    uint32_t esi;
    uint32_t ebp;
    uint32_t esp;
    uint32_t ebx;
    uint32_t edx;
    uint32_t ecx;
    uint32_t eax;
#endif // if defined(__arm__)
};

#pragma pack(pop)
#endif // ifndef __REGISTERS_H__