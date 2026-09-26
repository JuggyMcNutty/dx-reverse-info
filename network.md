# The network

How the original plays over a network: read from `Engine.dll`, which holds the
protocol -- connections, channels, replication and the joining handshake. The
sockets under it, the script's links and the master server are `IpDrv.dll`'s
([`IpDrv.dll`](ipdrv-dll.md)). What the fork has of any of it:
[multiplayer](natives.md#multiplayer).

Deus Ex's network code is Unreal Tournament's of its day -- native
replication lists and the world-stats challenge among it --, engine version
1100, with two Deus Ex additions (below). A client that joins the game's
servers speaks this protocol to the bit.

## The parts

- **The net driver** (`UNetDriver`; on the internet `IpDrv.dll`'s
  `TcpNetDriver`, over UDP) listens as a server or connects as a client, and
  ticks its connections: packets in first (`TickDispatch`, `0x10409670`), out
  last (`TickFlush`, `0x10409570`).
- **A connection** (`UNetConnection`) carries up to 1,023 channels: the
  control channel (0), which carries the handshake as text; one per actor the
  other side is told of; and file channels, for downloads.
- **The level** (`ULevel`) is the driver's listener: it accepts or refuses
  connections (`NotifyAcceptingConnection`, `0x1039ee60`: refused while the
  server travels) and channels (`NotifyAcceptingChannel`, `0x1039f290`: a
  server takes the control channel and file channels a client opens, a client
  only actor channels), and answers the handshake.
- **Demos** (`UDemoRecDriver`) write the same packets to a file.
- **The settings**, `[IpDrv.TcpNetDriver]` in `DeusEx.ini` (the GOG build's):
  `ConnectionTimeout` 15 s, `InitialConnectTimeout` 500 s, `AckTimeout` 1 s,
  `KeepAliveTime` 1 s, `MaxClientRate` 20,000 bytes a second,
  `RelevantTimeout` 5 s, `SpawnPrioritySeconds` 1, `ServerTravelPause` 4 s,
  `NetServerMaxTickRate` 20, `LanServerMaxTickRate` 35, `StaticUpdateRate` 12,
  `DynamicUpdateRate` 40, `AllowDownloads`.

## Joining

The control channel carries lines of text. The server's side is
`ULevel::NotifyReceivedText` (`0x1039f780`), the client's the pending level's
(`UNetPendingLevel`, `0x1040a880`).

1. **Client:** `HELLO REVISION=0 MINVER=1100 VER=1100`.
2. **Server:** `UPGRADE MINVER=1100 VER=1100`, and the connection closed,
   when the client's `VER` is below 1100 or its `MINVER` above (a missing one
   counts as 219); otherwise `CHALLENGE VER=` (the lower of the two versions)
   `CHALLENGE=` (a number from the CPU's clock) `STATS=` (whether the game
   logs world stats).
3. **Client:** `NETSPEED` and its rate in bytes a second -- `[Engine.Player]`'s
   `ConfiguredInternetSpeed` (2,600 in the GOG build's ini), its
   `ConfiguredLanSpeed` (20,000) with `?LAN` in the URL, as the Join LAN
   screen adds --; then `LOGIN RESPONSE=` (the engine's answer to the
   challenge) `URL=` the travel URL without the server's address or a
   `game=` option: the map (the default one when the address named none)
   and its options (`Name`, `Class`, `Team`, `Skin`, `Face`, `OverrideClass`,
   `PASSWORD`); with stats on, `Checksum=` an MD5 of the name and the stats
   password (`ngWorldSecret`), or `NoChecksum` without one.
4. **Server:** a wrong response gets `FAILURE CHALLENGE`. Then the game's
   `PreLogin` (script) may refuse: `FAILURE` and its message, `FAILCODE` and
   its code (the client's menu takes it: a password asked for), and the
   connection closed. Otherwise `WelcomePlayer` (`0x1039f500`): a `USES
   GUID= PKG= FLAGS= SIZE= GEN=` line per package the level needs, `WELCOME
   LEVEL=` (the map) `LONE=` (`bLonePlayer`), and `STATICRATE` and
   `DYNAMICRATE` from the settings.
5. **Client:** a file channel for each package it lacks, when the server
   allows downloads; with all in hand, the map loaded (below), then `HAVE
   GUID= GEN=` for each package whose generation here differs from the
   server's `GEN=` (the server counts only what the client's has), and `JOIN`
   -- not in a single player's game (`LONE=1`). `NETSPEED` again whenever the
   player sets one (the server takes one of at least 500, held to
   `MaxClientRate`).
6. **Server:** spawns the player (`SpawnPlayActor`, the game's `Login`, as an
   autonomous proxy), or answers `FAILURE` and the reason.

A client refused (`FAILURE`) goes back to its menu with `?failed`; a
`FAILCODE` goes to the console's `ConnectFailure` with the URL less its
password, for the menu to ask again; `UPGRADE` ends the join. `USERFLAG` sets
a number of the connection's either way; `DYNAMICRATE` and `STATICRATE` the
client notes.

- **The client's level** (`UGameEngine::LoadMap`): loaded as a client's
  (`NetMode` 3). Of the map's actors it keeps the static and no-delete ones,
  each with `Role` and `RemoteRole` exchanged, and destroys the rest -- the
  server sends them; no `GameInfo`, no `InitGame`; the begin-play events as a
  standalone level's. Until its player arrives, the level and the Entry level
  show `LevelAction` Connecting (`UGameEngine::Tick`).
- **The player** (`HandleClientPlayer`, `0x10405290`): the first bunch of a
  `PlayerPawn` the client owns (below), while the connection is still
  pending, makes it the client's: an autonomous proxy, the view's show flags
  and render map set, possessed by the viewport (`SetPlayer`, and
  `Possess`), input reset, `LevelAction` back to none, the connection open.

## Addresses

A URL names a server in what comes before its options (`?`) and portal
(`#`) (the URL parser, `0x103f7b60`): a `:` as the second character makes it
a file (a drive letter); a `:` further on, before any `.`, ends a protocol;
`//` may come before the host. The host is the text up to a `/`, when it has
a `.` past its first character not followed by the map's or a save's
extension (`dx`, `dxs`); after a `:` in it comes the port -- `[URL]`'s `Port`,
7,790, without one --, and after the `/` the map, the default map without
one. The Join screens join with the console's `open` and the address typed
or picked (Join LAN adds `?lan`).

## Packets

UDP datagrams of bits, first bit lowest. A number with a known maximum takes
as many bits as the maximum needs (`FBitWriter::WriteInt`).

- **A packet** (`UNetConnection::ReceivedPacket`, `0x10402fe0`): its number, 14
  bits (counting round 16,384); then acks and bunches; then a 1 bit and 0s to
  the byte, so the receiver finds the end from the last byte.
- **An ack:** a 1 bit and the number of a packet received (14 bits). A packet
  number the acks skip is taken as lost.
- **A bunch** (`SendRawBunch`, `0x104044d0`): a 0 bit; a control bit, then
  open and close bits if it is set; a reliable bit; the channel's index, 10
  bits; if reliable, the channel's own count of reliable bunches, 10 bits
  (round 1,024); if reliable or opening, the channel's type, 3 bits (1
  control, 2 actor, 3 file); the data's length in bits, up to the packet's
  size; the data.
- **Reliable bunches** are delivered in order: up to 128 wait for a gap to
  fill (`ReceivedRawBunch`, `0x103fb230`), duplicates are dropped, and a lost
  one is sent again.
- **Acks:** a packet is acknowledged as soon as its number is read, before
  its bunches; each acknowledgement goes again with the next packet's first
  new one.
- **The first bunches:** until the control channel's open is acknowledged,
  its unacknowledged bunches go again every second (`UChannel::Tick`,
  `0x103fae80`) -- a client's `HELLO` while the server comes up.
- **A reliable bunch** already had is dropped. An unreliable one opens a
  channel only if it closes it too: an actor sent once, to keep
  (`bNetTemporary`).
- **Timing:** an empty packet goes out when nothing has for `KeepAliveTime`,
  and a connection with nothing in for `ConnectionTimeout`
  (`InitialConnectTimeout` until its player is in) closes (`Tick`,
  `0x10404a40`). Sending stops for the tick when the bytes queued pass the
  connection's rate (`IsNetReady`).

## Numbering

Both sides number objects and names by the `USES` list (`UPackageMap::Compute`,
`0x1012c710`): the packages in the server's order, each one's objects (its
exports) and names numbered on from the last's. Where one side has an older
generation of a package, both count only what that generation had -- each
generation's export and name counts are in the file's header. A name in
several packages takes its first package's number. An older package file
(below version 68, as `CoreTexDetail.utx`) has no GUID in its header: its GUID
is the last of its heritage list, its one generation its counts.

- **An object:** a bit; 1 and a channel number for a dynamic actor (its actor
  channel on this connection; 0 for None or an actor without one), 0 and the
  object's number otherwise (`UPackageMapLevel::SerializeObject`,
  `0x104089f0`).
- **A name:** its number, up to the count of names; the count is None.
- **A class's fields:** numbered on from its parent class's: its own
  replicated properties and its net functions that override none, in the
  order of its package's exports (`0x1012c160`).
- **A value** (each property type's `NetSerializeItem`): a bool one bit; a
  byte its enum's bits (as many as its names need) or 8; an int or float 4
  bytes; an object or class as above, dropped unless of the property's
  class; a name as above; a string its length (with the terminator, as a
  compact index) and characters; a vector each coordinate rounded, in as many
  bits as the largest needs (given first, 4 bits), offset to be positive; a
  rotator each component's top byte, after a bit for whether it is not zero;
  a plane four 16-bit numbers; any other struct member by member.

## Replication

Each tick, for each connection with a player and room to send, the server
picks what to send (`ULevel::ServerTickClient`, `0x103a3500`):

- **The viewer:** where the player's view is (`PlayerCalcView`); every other
  tick, where it will be in 0.9 s, then 0.4 s, at its velocity, up to a wall.
- **The candidates:** each actor with a remote role once a tick -- every
  dynamic actor, and a static one if `bAlwaysRelevant` -- when its
  `NetUpdateFrequency` says an update is due (the actors spaced 0.023 s
  apart); sorted by priority (`0x103a4350`): the actor's net priority for the
  time since its last update (`SpawnPrioritySeconds` for one not yet sent),
  times 3 plus the cosine of its direction from the view, `bNetOptional`
  ones last.
- **Relevant or not** (`0x103a3120`), from the most important down, while the
  connection takes more: always if `bAlwaysRelevant`; if owned (up its
  `Owner`s) by the player or its view target, or one of them; if it has an
  `AmbientSound` and the viewer is within about half its sound's reach (√0.3
  of it); if a pawn inside the viewer's `RelevantRadius`; a pawn's weapon as
  its pawn. Not if hidden (`bHidden` or `bOnlyOwnerSee`) and neither
  blocking players nor sounding. Otherwise if seen: a line through the BSP
  from the viewer to it, or to a pawn's eyes.
- **Deus Ex's `AdditionalViews`:** a player's other viewpoints count as
  viewers too -- but the loop tries the first of the three, three times.
- **Channels:** a relevant actor whose class the client knows gets an actor
  channel; one irrelevant for `RelevantTimeout` loses it, and the client
  destroys its copy.

`UActorChannel::ReplicateActor` (`0x103fead0`) then writes what changed:

- **The first bunch** (`bNetInitial`): a static or no-delete actor by
  reference -- the client has it from the map --, any other by class and
  location, for the client to spawn.
- **Roles:** `bNetOwner` is whether the connection's player owns the actor; an
  autonomous proxy the client does not own goes as a simulated one.
- **Properties:** those the native list gives (`GetOptimizedRepList`, for
  `Actor`, `Pawn`, `PlayerPawn`, `Mover`, `ZoneInfo`, the two replication infos
  and `Inventory`), and each replicated script property whose value differs
  from what the client last got and whose class's condition holds (script,
  run once a call). What is lost is sent again.

**Receiving** (`UActorChannel::ReceivedBunch`, `0x103fd980`): a new channel's
first bunch names the actor, or its class and place; that actor is spawned
there without looking for room, its roles exchanged (a remote-owned spawn).
Each bunch then sets `bNetOwner` -- whether the actor's top owner is a player
pawn one of this machine's viewports plays --, and reads fields by number to
its end: a property (with an element byte in a static array), taken unless
the last value taken for it came in a later packet, when it is read and
dropped; or a function, run at once with its parameters (a bool is its bit,
any other a bit for whether it was sent, then its value). A run of
properties comes between the actor's `PreNetReceive` and `PostNetReceive`,
and a spawned actor gets `PostNetBeginPlay` after its first.

- **`PostNetReceive`** (`0x103680d0`): the new place, turn, base and collision
  go in through the calls that keep the level right -- the old values back,
  then a far move without the fit check, a move by nothing with the new turn,
  `SetCollisionSize`, `SetCollision`, and for a base each actor's `Bump` with
  the other, then `SetBase`. A moving simulated pawn eases to where the
  server has it: 100 units off or more, straight there; 40 to 100, a smooth
  move of 35% of the way, and a jump halfway if that left more than three
  quarters of the distance squared; under 40, a jump 15% of the way.
  `SimAnim` gives the animation: frame and last frame by 10,000, rate by
  5,000, tween by 1,000, a negative last frame for a loop (a pawn's
  `AnimMinRate` then at least 0.5). A mover's `SimInterpolate` gives its
  interpolation: alpha and rate by 100, the key and the previous one, and
  `PHYS_MovingBrush`. `bJustTeleported` clears. The local player's
  `PlayerReplicationInfo.Ping` loses half the client's average frame time.
- **Closing** an actor channel on a client destroys its actor
  (`UActorChannel::Destroy`, `0x103fd120`), unless it was sent to keep
  (`bNetTemporary`).

**Remote functions** (`AActor::ProcessRemoteFunction`, `0x103e5d90`): a
function marked for the net goes to the other side instead of running, when
its condition says so -- from the server to the client whose player owns the
actor, from a client to the server -- as its index and parameters on the
actor's channel. An unreliable one is dropped when the connection is full;
one a simulated proxy calls, not marked simulated, does not run.

## Deus Ex's additions

- **`Actor.RelevantRadius`:** a viewer with one takes every pawn inside it as
  relevant, seen or not.
- **`PlayerPawn.AdditionalViews[3]`:** more viewpoints for relevancy, of which
  only the first works.

## The database

The functions above are in `Engine.dll`'s database
([its database](engine-dll.md#the-database)), each with a one-line comment;
the pending level's handler, the relevancy test, the priority and its sort
are named there by hand.
