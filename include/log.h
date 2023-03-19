#ifdef ENABLE_LOGGING
// NO$GBA's Debug Messages
#define STRINGIFY_2(a) #a
#define STRINGIFY(a) STRINGIFY_2(a)
#define LOG(S) asm volatile("mov  r12,r12\n"                  \
                            "b SKIP" STRINGIFY(__LINE__) "\n" \
                            "#mystring:\n"                    \
                            ".short 0x6464\n"                 \
                            ".short 0\n"                      \
                            ".string \"%frame%: \"" #S "\n"   \
                            ".align 4\n"                      \
                            "SKIP" STRINGIFY(__LINE__) ":");
#else
#define LOG(S)
#endif
