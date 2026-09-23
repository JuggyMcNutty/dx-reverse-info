/* Types for DeusEx.exe (UE1 `Launch` module), transcribed from the Deus Ex SDK headers
 * in reference/ReleaseSDK1112f/Headers/DxHeaders.zip:
 *   Core/Inc/UnTemplate.h, Core/Inc/UnName.h, Core/Inc/Core.h, Window/Inc/Window.h
 *
 * Written C-style (explicit embedded bases) so IDA's parser accepts it; the SDK
 * originals are MSVC6-era C++ that IDA will not parse.
 *
 * EVERY size below is cross-checked against a real GMalloc allocation or field
 * offset observed in the binary. See the size ledger at the bottom.
 */

/* ---- Core containers ------------------------------------------------ */

struct FArray { void *Data; int ArrayNum; int ArrayMax; };   /* 12 */
struct FString { unsigned short *Data; int ArrayNum; int ArrayMax; }; /* 12 */
struct FName { int Index; };                                  /* 4  */

/* ---- Window.h: delegates -------------------------------------------- */

/* FDelegate is virtual -> carries a vtable pointer. */
struct FDelegate {
    void *__vftable;
    struct FCommandTarget *TargetObject;
    void *TargetInvoke;        /* ptr-to-member, single inheritance = 4 bytes */
};                                                            /* 12 */

struct FCommandTarget { void *__vftable; };                   /* 4  */

/* ---- Window.h: widget hierarchy ------------------------------------- */

struct WWindow {
    void *__vftable;           /* FCommandTarget vtable */
    void *hWnd;                /* HWND */
    struct FName PersistentName;
    unsigned short ControlId;
    unsigned short TopControlId;
    unsigned int Flags;        /* BITFIELD Destroyed:1, MdiChild:1 */
    struct WWindow *OwnerWindow;
    void *NotifyHook;          /* FNotifyHook* */
    void *Snoop;               /* FControlSnoop* */
    struct FArray Controls;    /* TArray<WControl*> */
};                                                            /* 44 */

struct WControl {
    struct WWindow base;
    void *WindowDefWndProc;    /* WNDPROC */
};                                                            /* 48 */

struct WLabel { struct WControl base; };                      /* 48 */

struct WButton {
    struct WControl base;
    struct FDelegate ClickDelegate;
    struct FDelegate DoubleClickDelegate;
    struct FDelegate PushDelegate;
    struct FDelegate UnPushDelegate;
    struct FDelegate SetFocusDelegate;
    struct FDelegate KillFocusDelegate;
};                                                            /* 120 */

struct WCoolButton {
    struct WButton base;
    void *hIcon;               /* HICON */
    unsigned int FrameFlags;
};                                                            /* 128 */

struct WListBox {
    struct WControl base;
    struct FDelegate DoubleClickDelegate;
    struct FDelegate SelectionChangeDelegate;
    struct FDelegate SelectionCancelDelegate;
    struct FDelegate SetFocusDelegate;
    struct FDelegate KillFocusDelegate;
};                                                            /* 108 */

struct WDialog { struct WWindow base; };                      /* 44 */

struct WWizardPage {
    struct WDialog base;
    struct WWizardDialog *Owner;
};                                                            /* 48 */

struct WWizardDialog {
    struct WDialog base;
    struct WCoolButton BackButton;
    struct WCoolButton NextButton;
    struct WCoolButton FinishButton;
    struct WCoolButton CancelButton;
    struct WLabel PageHolder;
    struct FArray Pages;       /* TArray<WWizardPage*> */
    struct WWizardPage *CurrentPage;
};                                                            /* 620 */

/* ---- Launch's own subclasses (reconstructed from the binary) --------- */

/* Each config page declares its OWN typed Owner pointer, separate from
 * WWizardPage::Owner -- this is why the derived members start at +52. */

struct WConfigPageRenderer {
    struct WWizardPage base;
    struct WWizardDialog *Owner;   /* +48 */
    struct WListBox RenderList;    /* +52  IDC_RenderList  1103 */
    struct WButton CompatibleButton; /* +160 IDC_Compatible 1109 */
    struct WButton AllButton;      /* +280 IDC_All         1110 */
    struct WLabel DescriptionLabel;/* +400 IDC_RenderNote  1104 */
    int CurrentIndex;              /* +448 */
    struct FArray Classes;         /* +452 std::vector-shaped, 12 bytes */
};                                                            /* 464 */

struct WConfigPageSafeMode {
    struct WWizardPage base;
    struct WWizardDialog *Owner;   /* +48 */
    struct WCoolButton RunButton;   /* +52  IDC_Run      1108 */
    struct WCoolButton VideoButton; /* +180 IDC_Video    1110 */
    struct WCoolButton SafeButton;  /* +308 IDC_SafeMode 1109 */
    struct WCoolButton WebButton;   /* +436 IDC_Web      1058 */
};                                                            /* 564 */

/* ---- Core.h: engine-global interface vtables ------------------------- */
/* NOTE: MSVC emits overload GROUPS in REVERSE declaration order, so the two
 * GetString overloads are swapped relative to Core/Inc/Core.h:195.
 * Confirm every call site by argument arity, not by index arithmetic. */

struct FConfigCacheVtbl {
    int  (*GetBool)(void *, const wchar_t *, const wchar_t *, int *, const wchar_t *);           /* +0  */
    int  (*GetInt)(void *, const wchar_t *, const wchar_t *, int *, const wchar_t *);            /* +4  */
    int  (*GetFloat)(void *, const wchar_t *, const wchar_t *, float *, const wchar_t *);        /* +8  */
    int  (*GetStringFStr)(void *, const wchar_t *, const wchar_t *, struct FString *, const wchar_t *); /* +12 <- reversed */
    int  (*GetStringBuf)(void *, const wchar_t *, const wchar_t *, wchar_t *, int, const wchar_t *);    /* +16 <- reversed */
    const wchar_t *(*GetStr)(void *, const wchar_t *, const wchar_t *, const wchar_t *);         /* +20 */
    int  (*GetSection)(void *, const wchar_t *, wchar_t *, int, const wchar_t *);                /* +24 */
    void *(*GetSectionPrivate)(void *, const wchar_t *, int, int, const wchar_t *);              /* +28 */
    void (*EmptySection)(void *, const wchar_t *, const wchar_t *);                              /* +32 */
    void (*SetBool)(void *, const wchar_t *, const wchar_t *, int, const wchar_t *);             /* +36 */
    void (*SetInt)(void *, const wchar_t *, const wchar_t *, int, const wchar_t *);              /* +40 */
    void (*SetFloat)(void *, const wchar_t *, const wchar_t *, float, const wchar_t *);          /* +44 */
    void (*SetString)(void *, const wchar_t *, const wchar_t *, const wchar_t *, const wchar_t *); /* +48 */
    void (*Flush)(void *, int, const wchar_t *);                                                 /* +52 */
    void (*Detach)(void *, const wchar_t *);                                                     /* +56 */
    void (*Init)(void *, const wchar_t *, const wchar_t *, int);                                 /* +60 */
    void (*Exit)(void *);                                                                        /* +64 */
    void (*Dump)(void *, void *);                                                                /* +68 */
};

struct FConfigCache { struct FConfigCacheVtbl *vtbl; };

struct FExecVtbl { int (*Exec)(void *, const wchar_t *, void *); };
struct FExec { struct FExecVtbl *vtbl; };

struct FMallocVtbl {
    void *(*Malloc)(void *, int, const wchar_t *);   /* +0 */
    void *(*Realloc)(void *, void *, int, const wchar_t *); /* +4 */
    void (*Free)(void *, void *);                    /* +8 */
};
struct FMalloc { struct FMallocVtbl *vtbl; };

/* ======================= SIZE LEDGER =================================
 * Each derived size is confirmed by an independent observation:
 *
 *   WWindow        44   (derived; anchors every size below)
 *   WControl       48   = 44 + WNDPROC
 *   WLabel         48   -> ConfigPageRenderer slot 400..448   OK
 *   WButton       120   -> ConfigPageRenderer slots 160,280   OK
 *   WCoolButton   128   -> ConfigPageSafeMode slots 52..564   OK
 *   WListBox      108   -> ConfigPageRenderer slot  52..160   OK
 *   WDialog        44   -> WWizardDialog total 620            OK
 *   WWizardPage    48   = 44 + Owner
 *   FDelegate      12   -> WButton 48+6*12=120                OK
 *   FString/FArray 12   -> stack locals at ebp-0x98/-0x94/-0x90 OK
 *
 *   WConfigPageRenderer 48+4+108+120+120+48+4+12 = 464  == GMalloc(464)  OK
 *   WConfigPageSafeMode 48+4+128*4               = 564  == GMalloc(564)  OK
 *   WWizardDialog       44+128*4+48+12+4         = 620  == ebp span 0x26C OK
 * ==================================================================== */
