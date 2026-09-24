"""IDA types for Render.dll's C++ structures.

Render.dll's one class, URender, and everything it works on -- the scene node,
the sprites, span buffers, BSP nodes and zones, the level, model and viewport
it reads through them, and the textures, light maps and cache items of its
lighting -- are C++ only, so tools/ida/ue1_types.py has no script to take them
from. These declarations follow the SDK's headers (Engine/Inc/UnRender.h,
UnObj.h, UnModel.h, UnLevel.h, UnCamera.h, UnTex.h, Core/Inc/UnCache.h,
Render/Src/RenderPrivate.h and UnSpan.h, in reference/ReleaseSDK1112f), up to
the fields the renderer uses, packed to 4 bytes as the DLLs are.

Run it in IDA (File > Script file, or the MCP's py_exec_file) on Render.dll's
database after tools/ida/ue1_types.py, whose script types it builds on. It
declares the structures, types URender's methods through their exports (each a
jump to the code), and names what is not exported: the sprite's constructor
and Setup, the light manager's methods and helpers, and the globals of the
weapon triangle and of the lighting. Running it again changes nothing.
"""
import ida_name
import ida_nalt
import ida_typeinf
import idc

DECLS = r"""
#pragma pack(push, 4)
struct FArrayRaw { void* Data; int ArrayNum; int ArrayMax; };
struct FTransArrayRaw { void* Data; int ArrayNum; int ArrayMax; void* Owner; };
struct FMemMarkRaw { void* Mem; unsigned char* Top; void* SavedChunk; };
struct FBoxRaw { FVector Min; FVector Max; unsigned char IsValid; };
struct FSpan { int Start; int End; struct FSpan* Next; };
struct FSpanBuffer { int StartY; int EndY; int ValidLines; struct FSpan** Index; void* Mem; struct FMemMarkRaw Mark; };
struct FTransform { FVector Point; unsigned char Flags; float ScreenX; float ScreenY; int IntY; float RZ; };
struct FActorLink { AActor* Actor; struct FActorLink* Next; };
struct FVolActorLink { FVector Location; AActor* Actor; struct FVolActorLink* Next; int Volumetric; };
struct FDynamicItem { void* vftable; struct FDynamicItem* FilterNext; float Z; };
struct FDynamicSprite
{
	void* vftable; struct FDynamicItem* FilterNext; float Z;
	struct FSpanBuffer* SpanBuffer; struct FDynamicSprite* RenderNext;
	struct FTransform ProxyVerts[4]; AActor* Actor;
	int X1; int Y1; int X2; int Y2; float ScreenX; float ScreenY; float Persp;
	struct FActorLink* Volumetrics; struct FVolActorLink* LeafLights;
	float ScaleGlow; float DrawScale; FVector Location; FRotator Rotation;
};
struct FDynamicLight { void* vftable; struct FDynamicItem* FilterNext; float Z; AActor* Actor; int IsVol; int HitLeaf; };
struct FBspNode
{
	FPlane Plane; unsigned __int64 ZoneMask; int iVertPool; int iSurf;
	int iBack; int iFront; int iPlane; int iCollisionBound; int iRenderBound;
	unsigned char iZone[2]; unsigned char NumVertices; unsigned char NodeFlags; int iLeaf[2];
};
struct FBspSurf
{
	UTexture* Texture; unsigned int PolyFlags; int pBase; int vNormal; int vTextureU; int vTextureV;
	int iLightMap; int iBrushPoly; short PanU; short PanV; AActor* Actor;
	struct FArrayRaw Decals; struct FArrayRaw Nodes;
};
struct FZoneProperties { AZoneInfo* ZoneActor; float LastRenderTime; unsigned __int64 Connectivity; unsigned __int64 Visibility; };
struct FLeaf { int iZone; int iPermeating; int iVolumetric; unsigned __int64 VisibleZones; };
struct FBspDrawList
{
	int iNode; int iSurf; int iZone; int Key; unsigned int PolyFlags;
	struct FSpanBuffer Span; AZoneInfo* Zone;
	struct FBspDrawList* Next; struct FBspDrawList* SurfNext;
	struct FActorLink* Volumetrics; void* Polys; struct FActorLink* SurfLights;
};
struct FSceneNode
{
	UViewport* Viewport; ULevel* Level;
	struct FSceneNode* Parent; struct FSceneNode* Sibling; struct FSceneNode* Child;
	int iSurf; int ZoneNumber; int Recursion; float Mirror;
	FPlane NearClip; FCoords Coords; FCoords Uncoords;
	struct FSpanBuffer* Span; struct FBspDrawList* Draw[3]; struct FDynamicSprite* Sprite;
	int X; int Y; int XB; int YB;
	float FX; float FY; float FX15; float FY15; float FX2; float FY2; float Zoom;
	FVector Proj; FVector RProj; float PrjXM; float PrjYM; float PrjXP; float PrjYP;
	FVector ViewSides[4]; FPlane ViewPlanes[4];
};
struct UViewport
{
	UObject obj; void* FOutputDevice_vt; void* FExec_vt;
	APlayerPawn* Actor; void* Console; unsigned int PlayerBits;
	float WindowsMouseX; float WindowsMouseY;
	int CurrentNetSpeed; int ConfiguredInternetSpeed; int ConfiguredLanSpeed;
	float StaticUpdateInterval; float DynamicUpdateInterval; unsigned char SelectedCursor;
	void* Canvas; void* Input; void* RenDev; UObject* MiscRes; FName Group;
	double LastUpdateTime; int SizeX; int SizeY; int ColorBytes; int FrameCount;
	unsigned int Caps; int Current; int Dragging; unsigned int RenderFlags; unsigned int ExtraPolyFlags;
	int TravelType; struct FArrayRaw TravelURL; int bTravelItems;
	double CurrentTime; unsigned char* ScreenPointer; int Stride;
	int HitTesting; int HitX; int HitY; int HitXL; int HitYL; struct FArrayRaw HitSizes;
	float SavedOrthoZoom; float SavedFovAngle; int SavedShowFlags; int SavedRendMap; int SavedMisc1; int SavedMisc2;
};
struct UModel
{
	UObject obj; struct FBoxRaw BoundingBox; FPlane BoundingSphere;
	void* Polys; struct FTransArrayRaw Nodes; struct FTransArrayRaw Verts; struct FTransArrayRaw Vectors;
	struct FTransArrayRaw Points; struct FTransArrayRaw Surfs;
	struct FArrayRaw LightMap; struct FArrayRaw LightBits; struct FArrayRaw Bounds; struct FArrayRaw LeafHulls;
	struct FArrayRaw Leaves; struct FArrayRaw Lights;
	int RootOutside; int Linked; int MoverLink; int NumSharedSides; int NumZones;
	struct FZoneProperties Zones[64];
};
struct ULevel
{
	UObject obj; void* FNetworkNotify_vt; struct FTransArrayRaw Actors;
	void* NetDriver; void* Engine; unsigned char URL[68]; void* DemoRecDriver;
	struct FArrayRaw ReachSpecs; struct UModel* Model; void* TextBlocks[16]; double TimeSeconds;
};
struct URender
{
	UObject obj; void* FExec_vt; void* Engine; struct FVolActorLink* FirstVolumetric;
	int Toggle; int LeakCheck; float GlobalMeshLOD; float GlobalShapeLOD; float GlobalShapeLODAdjust;
	int ShapeLODMode; float ShapeLODFix; double LastEndTime; double StartTime; double EndTime;
	unsigned int NodesDraw; unsigned int PolysDraw;
	struct FMemMarkRaw SceneMark; struct FMemMarkRaw MemMark; struct FMemMarkRaw DynMark; int SceneCount;
	int NetStats; int FpsStats; int GlobalStats; int MeshStats; int ActorStats; int FilterStats; int RejectStats;
	int SpanStats; int ZoneStats; int LightStats; int OcclusionStats; int GameStats; int SoftStats; int CacheStats;
	int PolyVStats; int PolyCStats; int IllumStats; int HardwareStats; int Extra6Stats; int Extra7Stats; int Extra8Stats;
	int NumPostDynamics; void** PostDynamics;
};
struct FMipmapBase { unsigned char* DataPtr; int USize; int VSize; unsigned char UBits; unsigned char VBits; };
struct FTextureInfo
{
	UTexture* Texture; unsigned __int64 CacheID; unsigned __int64 PaletteCacheID; FVector Pan;
	void* MaxColor; int Format; float UScale; float VScale; int USize; int VSize;
	int UClamp; int VClamp; int NumMips; int LOD; void* Palette; unsigned int Flags;
	struct FMipmapBase* Mips[12];
};
struct FLightMapIndex
{
	int DataOffset; int iLightActors; FVector Pan; float UScale; float VScale;
	int UClamp; int VClamp; unsigned char UBits; unsigned char VBits;
};
struct FCacheItem
{
	unsigned __int64 Id; unsigned char* Data; unsigned short Time; unsigned char Segment; unsigned char Extra;
	int Cost; struct FCacheItem* LinearNext; struct FCacheItem* LinearPrev; struct FCacheItem* HashNext;
};
struct FLightEffectInfo { void* Spatial; int SpatialChanges; int BrightnessWavers; };
#pragma pack(pop)
"""

# Sizes the headers and the registration give: a check that the packing holds.
SIZES = {"FSceneNode": 0x16C, "FDynamicSprite": 0xDC, "FBspNode": 0x40, "FZoneProperties": 0x18, "URender": 0xF4,
         "FTextureInfo": 0x80, "FLightMapIndex": 0x28, "FCacheItem": 0x20}

FRAME = "struct URender *this, struct FSceneNode *Frame"
MESH = FRAME + (", AActor *Owner, AActor *LightSink, struct FSpanBuffer *SpanBuffer, AZoneInfo *Zone,"
                " const FCoords *Coords, struct FVolActorLink *LeafLights, struct FActorLink *Volumetrics, unsigned int PolyFlags")
METHODS = {
    "?SetupDynamics@URender@@QAEXPAUFSceneNode@@PAVAActor@@@Z": "void __thiscall f(%s, AActor *Exclude);" % FRAME,
    "?OccludeFrame@URender@@QAEXPAUFSceneNode@@@Z": "void __thiscall f(%s);" % FRAME,
    "?OccludeBsp@URender@@QAEXPAUFSceneNode@@@Z": "void __thiscall f(%s);" % FRAME,
    "?DrawFrame@URender@@QAEXPAUFSceneNode@@@Z": "void __thiscall f(%s);" % FRAME,
    "?DrawWorld@URender@@UAEXPAUFSceneNode@@@Z": "void __thiscall f(%s);" % FRAME,
    "?PreRender@URender@@UAEXPAUFSceneNode@@@Z": "void __thiscall f(%s);" % FRAME,
    "?PostRender@URender@@UAEXPAUFSceneNode@@@Z": "void __thiscall f(%s);" % FRAME,
    "?DrawActor@URender@@UAEXPAUFSceneNode@@PAVAActor@@@Z": "void __thiscall f(%s, AActor *Actor);" % FRAME,
    "?DrawActorSprite@URender@@QAEXPAUFSceneNode@@PAUFDynamicSprite@@@Z":
        "void __thiscall f(%s, struct FDynamicSprite *Sprite);" % FRAME,
    "?DrawMesh@URender@@QAEXPAUFSceneNode@@PAVAActor@@1PAVFSpanBuffer@@PAVAZoneInfo@@ABVFCoords@@PAUFVolActorLink@@PAUFActorLink@@K@Z":
        "void __thiscall f(%s);" % MESH,
    "?DrawLodMesh@URender@@QAEXPAUFSceneNode@@PAVAActor@@1PAVFSpanBuffer@@PAVAZoneInfo@@ABVFCoords@@PAUFVolActorLink@@PAUFActorLink@@K@Z":
        "void __thiscall f(%s);" % MESH,
    "?LeafVolumetricLighting@URender@@QAEXPAUFSceneNode@@PAVUModel@@H@Z":
        "void __thiscall f(%s, struct UModel *Model, int iLeaf);" % FRAME,
    "?BoundVisible@URender@@UAEHPAUFSceneNode@@PAVFBox@@PAVFSpanBuffer@@AAUFScreenBounds@@@Z":
        "int __thiscall f(%s, struct FBoxRaw *Bound, struct FSpanBuffer *SpanBuffer, void *Results);" % FRAME,
    "?CreateMasterFrame@URender@@UAEPAUFSceneNode@@PAVUViewport@@VFVector@@VFRotator@@PAUFScreenBounds@@@Z":
        "struct FSceneNode * __thiscall f(struct URender *this, struct UViewport *Viewport, FVector Location, FRotator Rotation, void *Bounds);",
    "?CreateChildFrame@URender@@UAEPAUFSceneNode@@PAU2@PAVFSpanBuffer@@PAVULevel@@HHMABVFPlane@@ABVFCoords@@PAUFScreenBounds@@@Z":
        "struct FSceneNode * __thiscall f(struct URender *this, struct FSceneNode *Parent, struct FSpanBuffer *Span, struct ULevel *Level,"
        " int iSurf, int iZone, float Mirror, const FPlane *NearClip, const FCoords *Coords, void *Bounds);",
    "?FinishMasterFrame@URender@@UAEXXZ": "void __thiscall f(struct URender *this);",
}

# Not exported: jumps and data of this build of Render.dll (imagebase 0x10b00000).
JUMPS = {
    0x10B0117C: ("FDynamicSprite_ctor",
                 "struct FDynamicSprite * __thiscall f(struct FDynamicSprite *this, struct FSceneNode *Frame, int iNode, AActor *Actor);"),
    0x10B010E6: ("FDynamicSprite_Setup", "int __thiscall f(struct FDynamicSprite *this, struct FSceneNode *Frame);"),
    # The light manager: its vtable's entries, in FLightManagerBase's order, and its helpers.
    0x10B01159: ("FLightManager_Init", "void __thiscall f(void *this);"),
    0x10B01154: ("FLightManager_Exit", "void __thiscall f(void *this);"),
    0x10B010B9: ("FLightManager_SetupForActor",
                 "unsigned int __thiscall f(void *this, struct FSceneNode *Frame, AActor *Actor, struct FVolActorLink *LeafLights,"
                 " struct FActorLink *Volumetrics);"),
    0x10B0122B: ("FLightManager_SetupForSurf",
                 "void __thiscall f(void *this, struct FSceneNode *Frame, FCoords *FacetCoords, struct FBspDrawList *Draw,"
                 " struct FTextureInfo **LightMap, struct FTextureInfo **FogMap, int Merged);"),
    0x10B01168: ("FLightManager_FinishSurf", "void __thiscall f(void *this);"),
    0x10B0103C: ("FLightManager_FinishActor", "void __thiscall f(void *this);"),
    0x10B01271: ("FLightManager_Light", "FPlane *__thiscall f(void *this, FPlane *result, void *Point, unsigned int ExtraFlags);"),
    0x10B011F4: ("FLightManager_Fog", "FPlane *__thiscall f(void *this, FPlane *result, void *Point, unsigned int ExtraFlags);"),
    0x10B01122: ("FLightManager_AddLight", "int __stdcall f(AActor *Owner, AActor *Light);"),
    0x10B0100F: ("FLightManager_SetupLight", "void __thiscall f(void *this, struct FTextureInfo *Map, struct FSceneNode *Frame);"),
    0x10B01217: ("FLightManager_ShadowFromBits", "void __stdcall f(struct FTextureInfo *Map, unsigned char *Bits, unsigned char *Dest);"),
    0x10B010FF: ("FLightManager_MergeLight", None),
}
DATA = {
    0x10B4EA08: ("GWeaponCoords", "FCoords GWeaponCoords;"),
    0x10B4EB10: ("GMeshHadWeaponTriangle", "int GMeshHadWeaponTriangle;"),
    0x10B2A93C: ("FLightManager_vftable", "void *FLightManager_vftable[8];"),
    0x10B3D2F0: ("GLightManagerObject", "void *GLightManagerObject;"),
    0x10B2A0F0: ("GLightEffects", "struct FLightEffectInfo GLightEffects[20];"),
    0x10B49E20: ("GLightMapInfo", "struct FTextureInfo GLightMapInfo;"),
    0x10B3D2F8: ("GFogMapInfo", "struct FTextureInfo GFogMapInfo;"),
    0x10B401C0: ("GLightInfos", "int GLightInfos[9472];"),
    0x10B49DF4: ("GLastLightInfo", "int *GLastLightInfo;"),
    0x10B49DFC: ("GNumStaticLights", "int GNumStaticLights;"),
    0x10B3CADC: ("GNumAnimatedLights", "int GNumAnimatedLights;"),
    0x10B3CAC8: ("GNumMovingLights", "int GNumMovingLights;"),
    0x10B49E04: ("GRebuildStaticMap", "int GRebuildStaticMap;"),
}


def jump_target(ea):
    return idc.get_operand_value(ea, 0) if idc.print_insn_mnem(ea) == "jmp" else None


def main():
    if ida_nalt.get_root_filename().lower() != "render.dll":
        print("render_types: not Render.dll, nothing done")
        return
    errors = ida_typeinf.parse_decls(None, DECLS, None, ida_typeinf.HTI_DCL | ida_typeinf.HTI_PAKDEF)
    til = ida_typeinf.get_idati()
    for name, size in SIZES.items():
        t = ida_typeinf.tinfo_t()
        if not t.get_named_type(til, name) or t.get_size() != size:
            print("render_types: %s is not 0x%x bytes" % (name, size))
    typed = 0
    for export, proto in METHODS.items():
        ea = ida_name.get_name_ea(idc.BADADDR, export)
        body = jump_target(ea) if ea != idc.BADADDR else None
        if body and idc.SetType(body, proto):
            typed += 1
        else:
            print("render_types: could not type %s" % export)
    for ea, (name, proto) in JUMPS.items():
        body = jump_target(ea)
        if body is None:
            print("render_types: no jump at 0x%x" % ea)
            continue
        ida_name.set_name(ea, "j_" + name, ida_name.SN_NOWARN | ida_name.SN_FORCE)
        ida_name.set_name(body, name, ida_name.SN_NOWARN | ida_name.SN_FORCE)
        if proto:
            idc.SetType(body, proto)
    for ea, (name, decl) in DATA.items():
        ida_name.set_name(ea, name, ida_name.SN_NOWARN | ida_name.SN_FORCE)
        idc.SetType(ea, decl)
    print("render_types: %d declaration errors; %d of %d methods typed; %d helpers and %d globals named"
          % (errors, typed, len(METHODS), len(JUMPS), len(DATA)))


main()
