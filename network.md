# The network

How the original plays over a network: read from `Engine.dll`, which holds the
protocol -- connections, channels, replication and the joining handshake. The
sockets under it, the script's links and the master server are `IpDrv.dll`'s
([`IpDrv.dll`](ipdrv-dll.md)). What the fork has of any of it:
[multiplayer](https://github.com/JuggyMcNutty/VibeEngine/blob/deusex/vibe/docs/NATIVES.md#multiplayer).

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

A server listens once a map is opened with `?listen` (`ULevel::Listen`,
`0x1039e7c0`): the net driver `[Engine.Engine]`'s `NetworkDevice` names binds
the URL's port -- before the game's `InitGame`, which sees a listen server
(dedicated without a client) --, and the game engine's `ServerActors` are
spawned, from the section of the class `[Engine.Engine]`'s `GameEngine` names
(`[DeusEx.DeusExGameEngine]`): each a class and then `Key=Value` settings of
its config properties -- the LAN beacon (`IpDrv.UdpBeacon`, answering
`REPORT` and `REPORTQUERY` on port 8,777), the query answerer
(`IpServer.UdpServerQuery`, GameSpy's `\basic\`, `\info\`, `\rules\` and
`\players\` on the first free port after the game's), and the master
servers' uplinks (`IpServer.UdpServerUplink`, which announce the server
only with `DoUplink` set: [the master server](ipdrv-dll.md#the-master-server)). The level's
`NextSwitchCountdown` is set to `ServerTravelPause`. The level's
`EngineVersion` and `MinNetVersion`, which the query answerer reports and
the Join screens compare, are Deus Ex's 1100; its `ComputerName` is the
machine's (Windows' computer name).

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
   `PASSWORD` -- those the player has: from the game's `User.ini`, whose
   `[DefaultPlayer]` holds `Name` and `Class`, a login carries only those);
   with stats on (`STATS=1`: the server's game's `bWorldLog`), `Checksum=`
   the MD5 of the viewport player's `PlayerReplicationInfo.PlayerName` then
   its `ngWorldSecret`, each as UTF-16 without the terminator, in 32
   lowercase hex digits -- `Checksum=NoChecksum` when the password is
   empty; without stats, nothing (`0x1040a880`).
4. **Server:** a wrong response gets `FAILURE CHALLENGE`. Then the game's
   `PreLogin` (script) may refuse: `FAILURE` and its message, `FAILCODE` and
   its code (the client's menu takes it: a password asked for), and the
   connection closed. Otherwise `WelcomePlayer` (`0x1039f500`): a `USES
   GUID= PKG= FLAGS= SIZE= GEN=` line per package of the server's list,
   made as the map opened (`UGameEngine::BuildServerMasterMap`,
   `0x10388b10`) -- the map's own, then each of
   the `ServerPackages` in the game engine's section (none in the GOG
   build's ini; each logged `Server Package: <name>`), then the package of
   the game's class; each followed by what it imports, depth first (each
   package's imports, in its import table's order, straight after it); none
   twice, and none flagged server-side only (Deus Ex's `IpDrv`, `IpServer`,
   `UWindow`, `UBrowser`) --, `WELCOME
   LEVEL=` (the map) `LONE=` (`bLonePlayer`), and `STATICRATE` and
   `DYNAMICRATE` from the settings.
5. **Client:** each package it lacks downloaded, one at a time
   ([downloads](#downloads)); with all in hand, the map loaded (below), then `HAVE
   GUID= GEN=` for each package whose generation here differs from the
   server's `GEN=` (the server counts only what the client's has), and `JOIN`
   -- not in a single player's game (`LONE=1`). `NETSPEED` again whenever the
   player sets one (the server takes one of at least 500, held to
   `MaxClientRate`).
6. **Server:** spawns the player (`SpawnPlayActor`, the game's `Login`, as an
   autonomous proxy), or answers `FAILURE` and the reason.

A client refused (`FAILURE`) or told `UPGRADE` stays in the level it was
in, shown why ([what the player sees](#what-the-player-sees-of-a-join)); a
`FAILCODE` goes to the console's `ConnectFailure` with the URL less its
password, for the menu to ask again. `USERFLAG` sets
a number of the connection's either way; `DYNAMICRATE` and `STATICRATE` the
client keeps each as a time between updates -- 1 s over the rate, 0.01 s to
1 s, none for 0 -- which Deus Ex's `ReplicateMove` paces the player's moves
by.

- **The client's level** (`UGameEngine::LoadMap`): loaded as a client's
  (`NetMode` 3). Of the map's actors it keeps the static and no-delete ones,
  each with `Role` and `RemoteRole` exchanged, and destroys the rest -- the
  server sends them; no `GameInfo`, no `InitGame`; the begin-play events as a
  standalone level's. Until its player arrives, the level and the Entry level
  show `LevelAction` Connecting (`UGameEngine::Tick`).
- **The player** (`HandleClientPlayer`, `0x10405290`): the first bunch of a
  `PlayerPawn` the client owns (below), while the connection is still
  pending, makes it the client's: the viewport takes the connection's speed
  and the two update intervals, the pawn is an autonomous proxy with the
  view's show flags and render map set, possessed by the viewport
  (`SetPlayer`, and `Possess`), input reset, `LevelAction` back to none, the
  connection open.

## Downloads

**Which** (the client's `WELCOME`, `UNetPendingLevel::NotifyReceivedText`):
each `USES` package is looked for with its GUID
([a package's file](core-dll.md#packages-and-linkers)) -- on the paths by
its name, else in the cache by its GUID --, and one not found, with no
`<name>.dll` either, is needed (`PKG_Need`, `0x8000`, added to its flags).
One needed while the client's `AllowDownloads` is off, or whose `FLAGS` lack
`AllowDownload` (`0x1`), ends the join: `Downloading '<name>' not allowed`,
the connection closed. Otherwise the first needed one is asked for and the
join counts as welcomed; its map loads when none is needed any more. A file
found whose GUID is not the server's -- a same-named package on the paths
-- fails the join as the map loads: `Package '<name>' version mismatch`
(Core's `PackageVersion`).

**Asking** (`UNetConnection::ReceiveFile`, `0x10405490`): a file channel
(type 3), named after the package, and in one reliable bunch the GUID's four
words; with no channel free, the download fails with `ChAllocate`.

**Sending** (`UFileChannel::ReceivedBunch`, `0x103ffff0`, a server's side):
the GUID is looked up in the connection's package list among the packages
flagged `AllowDownload`, the only ones whose file is known
(`FPackageInfo`'s `URL`); the level asked (`NotifySendingFile`: a server's
lets its clients have any -- `Client requested file: Allowed` --, a client's
refuses a server); the file opened, logged `Sending '<file>'` (`NetSend`).
Anything else is logged `Received invalid file request` (`NetInvalid`) and
answered with an empty bunch that closes the channel. Then each tick
(`UFileChannel::Tick`, `0x10400780`), while the channel's reliable buffer
has room -- the rate left out (`IsNetReady(1)`) --, a reliable bunch of as
much of the file as the packet has room for (`MaxSendBytes`: the packet's
bits less its header, its trailer and a bunch header's 64, in bytes), the
packet sent after each; the bunch that ends the file closes the channel. A
file channel on either side has its connection send a packet every tick
(`TimeSensitive`), so the client's acks keep the server's buffer draining.

**Receiving** (the same functions, a client's side): the first bunch opens
a temporary file in `CachePath`, the folder made first
([the cache's files](core-dll.md#packages-and-linkers)), logged `Receiving
package '<name>'`; each bunch's bytes go into it, and the player is shown
`Receiving '<name>' (F10 Cancels)` and `Size <n>K, Complete <n>%` for 4 s
(`Engine.int`'s `ReceiveFile` and `ReceiveSize`; the size the `USES`
line's). A failed open or write closes the channel with `NetOpen` or
`NetWrite`. When the channel goes (`UFileChannel::Destroy`,
`0x10400a40`): nothing received is `Server refused to send '<name>'`
(`NetRefused`), a size other than the `USES` line's is `NetSize`, a failed
move `NetMove`; else the file is moved to `<CachePath>\<GUID>.uxx` -- the
extension written in, not `CacheExt` -- and the player is shown `Success`
and `Received '<name>'`. The pending level is told either way
(`NotifyReceivedFile`, `0x1040bda0`): an error fails the join
(`Downloading package '<name>' failed: <error>`, the first error kept); a
success clears the package's `PKG_Need` and asks for the next. A failed
download's temporary file is left for the cache's next cleaning.

**Going** (`UGameEngine::LoadMap`, `0x1038c1f0`): a package stays loaded
while anything uses it, and a map load collects the garbage once the new
map is in (`CollectGarbage`, keeping what is native): a server's
downloads go at the next map that does not use them -- the menu's map
after a `DISCONNECT` --, so another server's package of that name loads in
their place. Its version is checked as the map loads, before that
collection (`GetPackageLinker`'s GUID), so -- read, not tried -- joining
that other server straight from the first one's level, or from the Entry
level a lost server left, would find the old version still loaded:
`Package '<name>' version mismatch`.

## What the player sees of a join

`UGameEngine::SetProgress` (`0x10389e00`) sets the first viewport's
player's `ProgressMessage[0]` and `[1]`, their `ProgressColor`s white, and
`ProgressTimeOut` to the level's time plus the seconds given; -1 s calls
the player's `ShowUpgradeMenu` first. The console's `Tick` calls the
player's `ShowProgress` while that time is ahead: Deus Ex's opens
`MultiplayerMessageWin`, which draws the two lines centred in blue and sends
`CANCEL` for F10.

- **Connecting.** While a join is pending, each frame drawn
  (`UpdateConnectingMessage`, `0x10388900`, from `UGameEngine::Draw`): when
  no progress shows, `Connecting (F10 Cancels):` and
  `deusex://<host>/<map>` (`ConnectingText`, `ConnectingURL`) for 60 s.
- **Failing.** A pending level with an error (`UGameEngine::Tick`,
  `0x1038fe90`): `Connection failed` and the error for 4 s, logged
  `Pending connect to '<url>' failed; <error>`, and the pending level
  deleted; the level plays on. Its own tick (`0x1040c170`) makes a closed
  connection's error `Connection failed`; a map failing to load as the
  client's shows the same with the load's error. The server's `FAILURE`:
  first `Rejected By Server` and its text for 10 s, the error `Rejected By
  Server: <text>`, the connection closed. `UPGRADE` with a `MINVER` of 1,100
  or less: `Connection failed` and `Server's version is outdated` for 6 s;
  above, the upgrade menu. No net driver for the URL (`UGameEngine::Browse`,
  `0x1038ad30`): `Networking Failed` and the error for 6 s. A browse to a
  server cancels a join already pending.
- **Lost.** A client level whose server connection closes
  (`ULevel::TickNetClient`, `0x103a3030`), or which the server sends
  `FAILURE` after the join (`ULevel::NotifyReceivedText`), browses
  `?failed` (`?entry` alike, less the message): `Browse` logs `Failed;
  returning to Entry`, drops the level's net driver, makes the Entry level
  the one played with no level action and spawns a player there for each
  viewport; with no join pending, `Connection failed` shows for 6 s. The
  next map's load destroys that player, as it does each viewport's actor
  where it stands.
- **The game engine's commands** (`UGameEngine::Exec`, `0x1038a030`):
  `CANCEL`, with a join pending, `Cancelled Connect Attempt` for 2 s, else
  the progress cleared, then the pending level deleted (`CancelPending`,
  `0x1038ac50`); `DISCONNECT`, travel to `dx.dx` (Deus Ex's
  `DeusExPlayer.DisconnectPlayer` sends it -- the menu's disconnect, and the
  game's `ForceDisconnect`); `RECONNECT`, travel to the last URL.
- **The viewport's** (`UViewport::Exec`, `0x10373a60`): `NETSPEED <rate>`
  keeps the rate as `[Engine.Player]`'s `ConfiguredInternetSpeed` (saved),
  and on a server joined without `?LAN`, with a rate of 500 or more, sets
  the connection's speed, held to the driver's `MaxClientRate`, and the
  viewport's, and sends `NETSPEED <rate>`. `LANSPEED` does the same for a
  `?LAN` server -- and keeps its rate as `ConfiguredInternetSpeed` too, the
  field `NETSPEED` writes (the connection takes `ConfiguredLanSpeed`, the
  next one, for `?LAN`).

## Server travel

A server moves its game to another map, and its clients follow (seen
between the two engines, 2026-09-27):

1. **The level's `ServerTravel(URL, bItems)`** (script; the game engine's
   `SERVERTRAVEL <url>` calls it, and a game's own map change): Deus Ex's
   does nothing in a standalone game; otherwise, unless a travel is already
   set, `NextURL` and `bNextItems` are set and the game's
   `ProcessServerTravel` runs -- or, with no game, `NextSwitchCountdown` 0.
2. **`GameInfo.ProcessServerTravel`** (script): `ClientTravel(URL,
   TRAVEL_Relative, bItems)` to each remote player's pawn -- a replicated
   call --, `PreClientTravel` for the host's own, whose `Skin`, `Face`,
   `Team`, `Name` and `Class` a listen server appends to `NextURL`; a game
   that is not networked switches at once (countdown 0).
3. **The server** refuses no one but takes no one new while `NextURL` is
   set: `NotifyAcceptingConnection` ignores a new client's packets
   (`Server <level> refused`). Once `NextSwitchCountdown` -- the
   `ServerTravelPause` 4 s it was given when the map began listening --
   runs out (`UGameEngine::Tick`): `Server switch level: <url>`, the
   players' travel info taken when `bNextItems` is set, and a browse to
   `NextURL` relative to the last URL, whose options -- `?listen`, the
   game -- it keeps; the old net driver goes with its level, closing the
   clients' connections, and the new map listens again.
4. **A client**: the `ClientTravel` browses relative to its last URL --
   the server's address, the next map --, a new join that the server
   ignores until it listens again, the handshake's first packets sent
   again meanwhile. When the old level's connection closes, the client
   browses `?failed` and goes to its Entry level (`Failed; returning to
   Entry`), showing no failure while the join is pending; the join then
   loads the next map.

## Addresses

A URL names a server in what comes before its options (`?`) and portal
(`#`) (the URL parser, `0x103f7b60`): a `:` as the second character makes it
a file (a drive letter); a `:` further on, before any `.`, ends a protocol;
`//` may come before the host. The host is the text up to a `/`, when it has
a `.` past its first character not followed by the map's or a save's
extension (`dx`, `dxs`); after a `:` in it comes the port -- `[URL]`'s `Port`,
7,790, without one, as any URL's port --, and after the `/` the map, the
default map without one. The Join screens join with the console's `open` and the address typed
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
- **Merging** (`UChannel::SendBunch`, `0x103fb6b0`): a channel's bunch goes
  into the last one sent, one header for both, when that one is the same
  channel's and still ends the packet being built -- no ack written since
  (`SendAck` stops it), no `FlushNet` either -- and the two fit the packet
  with 9 bytes to spare; a reliable one keeps its record and sequence
  number. Actor updates, text and remote calls may merge; a file's bunches
  and a channel's close never do.
- **Acks:** a packet is acknowledged as soon as its number is read, before
  its bunches; each acknowledgement goes again with the next packet's first
  new one.
- **The first bunches:** until the control channel's open is acknowledged,
  its unacknowledged bunches go again every second (`UChannel::Tick`,
  `0x103fae80`) -- a client's `HELLO` while the server comes up.
- **A reliable bunch** already had is dropped. An unreliable one opens a
  channel only if it closes it too: an actor sent once, to keep
  (`bNetTemporary`). A channel the other side opens is open and acknowledged
  here from its opening bunch, whose packet it keeps as its open's.
- **Timing:** a packet goes out at the end of a tick that sent a bunch;
  otherwise, with the acks' second copies (written every tick), when nothing
  has for `KeepAliveTime`. A connection with nothing in for
  `ConnectionTimeout` (`InitialConnectTimeout` until it is open and its
  player in; a server's connection is open from a client's first packet,
  [`UTcpNetDriver::TickDispatch`](ipdrv-dll.md)) closes (`Tick`,
  `0x10404a40`). Sending stops for the tick when the bytes
  queued pass the connection's rate (`IsNetReady`).
- **Frames:** a client runs at most its connection's speed over 64 frames a
  second -- 40 at 2,600 --, a dedicated server (the game started with
  `-SERVER`, no client: [the command line](cli-flags.md)) at
  `NetServerMaxTickRate` (`LanServerMaxTickRate` with `-lanplay`), 10 to
  120 (`UGameEngine::GetMaxTickRate`, `0x1038fc60`); a listen server as
  fast as its client draws. A dedicated server has no window, player or
  console of its own, and its map listens without `?listen`.

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
  tick, where it will be in 0.9 s -- 0.4 s every fourth tick -- at its and
  its base's velocity, up to a wall.
- **The candidates:** each actor with a remote role once a tick -- every
  dynamic actor, and a static one if `bAlwaysRelevant` -- when its
  `NetUpdateFrequency` says an update is due: the whole number of updates
  since the connection's last replication changed, each actor's clock 0.023 s
  on from the one before it. An actor a client was sent to keep
  (`bNetTemporary`) is never one again for that client.
- **Priority** (`0x103a4350`): the actor's `GetNetPriority` -- its
  `NetPriority` times the time since its last complete update
  (`SpawnPrioritySeconds` for one without a channel, so an unsent actor does
  not rise) -- times 3 plus the cosine between the player's view direction
  and the actor's direction from the viewer, in 65,536ths; `bNetOptional`
  ones 100,000 lower. A walking player's pawn (`APawn::GetNetPriority`,
  `0x103c5ff0`) takes, for the time, twice the distance between where it will
  be in half the lag and where the client's copy would be by then, over its
  `GroundSpeed`, plus half the time. The candidates go highest first.
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
  channel, and is replicated when the channel has room; one irrelevant for
  `RelevantTimeout` loses it, and the client destroys its copy. A destroyed
  actor's channels close (`UNetDriver::NotifyActorDestroyed`, `0x10409d70`).

`UActorChannel::ReplicateActor` (`0x103fead0`) then writes what changed,
against a copy of what this client last got (`SetChannelActor`,
`0x103fd620`): the class's defaults to begin with, less its config values --
cleared, so that they always go, the client's own config being its own --;
an actor sent to keep has no copy and is compared with its defaults.

- **The first bunch** (`bNetInitial`): a static or no-delete actor by
  reference -- the client has it from the map --, any other by class and
  location, for the client to spawn. It is reliable, except for an actor sent
  to keep, whose one unreliable bunch opens and closes the channel; the
  actor is then one of the connection's sent temporaries -- until the channel
  goes with its open never acknowledged, when it can go again.
- **Roles:** `bNetOwner` is whether the connection's player owns the actor
  (its top owner that player's pawn); an autonomous proxy goes as a simulated
  one unless the client owns it or it has no instigator (or its instigator
  was last sent as owned). `Role` and `RemoteRole` each go under the other's
  field number, the roles as the client has them. `bSimulatedPawn` is a pawn
  sent as a simulated proxy.
- **Properties:** those the native list gives (`GetOptimizedRepList`, for
  `Actor`, `Pawn`, `PlayerPawn`, `Mover`, `ZoneInfo`, the two replication infos
  and `Inventory`), and each replicated script property whose value differs
  from what the client last got and whose replication statement holds (the
  statement its `RepOwner` names, each evaluated once a call). The classes
  with a native list declare `nativereplication`, and the class net cache
  leaves their own properties out of the script replication
  (`UPackageMap::GetClassNetCache`, Core `0x1012c160`), so their statements
  are never evaluated -- the [native lists](#the-native-lists) decide. A reference to a dynamic actor the client has no channel for yet
  compares as None, so it goes once there is one; one that went before the
  client could resolve it is cleared from the copy, so it goes again. An
  always-relevant inventory item sends its script classes' values in its
  first bunch only (`AInventory::ShouldDoScriptReplication`, `0x10367e00`).
- **Losses:** each element's last packet and whether it was reliable are kept;
  a lost unreliable one is sent again with the next, and once the client
  acknowledges the channel's open, so is all that went unreliably before it.
- **A full bunch** keeps the rest for the next tick; the time since the last
  update runs on until one goes complete.

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

**On a server** a client's bunch is taken with the roles as the client has
them: a property value or a call only when its replication statement then
holds and the client owns the actor -- anything else is read and dropped
("unwanted").

**Animation** goes packed into `SimAnim` (the `PostNetReceive` scale above),
set where the animation starts rather than when replicated: `PlayAnim`
(`0x103e0160`) sets all four, an unchanged one's last frame nudged up by 1 so
that it still goes; `LoopAnim` (`0x103e05e0`) all four with the last frame
negative, or, on the loop already playing, the rate and last frame, nudged
alike; `TweenAnim` (`0x103e0bd0`) the frame and tween with no rate or last
frame; and a one-shot
animation that ends on an actor with a lower remote role than simulated (and
not a weapon) sets the frame and rate where it stopped.

**Remote functions** (`AActor::ProcessRemoteFunction`, `0x103e5d90`): every
call of an actor's script function in a net game -- and of a native without
its own number -- passes this first. A simulated or dumb proxy runs only
functions marked simulated. A function marked for the net goes to the other
side instead of running when its condition holds -- the first declaration's,
from its class's replication block, evaluated for the actor: from the server
to the client whose player owns the actor (its top owner a player pawn whose
`Player` is a net connection) -- a channel opened for the actor, and the
actor sent first, if that client has none --, from a client to the server,
and from a client only on an actor the server gave it a channel for. It goes as
its field number and its parameters (a bool its bit, any other a bit for
whether it is not zero, then its value), reliable as the function is marked;
an unreliable one is dropped when the connection has no room.

**Ticking by role** (`AActor::Tick`, `0x103a1aa0`): another player's pawn on a
client (a simulated proxy) moves smoothly along its velocity -- a player's,
off the ground by a trace 8 units down and not flying or in water, gaining
half the zone's gravity -- and runs its `Tick`: no state code, timers or
physics. A dumb proxy only falls. The local player's pawn runs its input,
`PlayerInput`, `PlayerTick`, state code and timers, but its physics only in
its moves (`AutonomousPhysics`). A client's pawn on the server (remote role
autonomous) runs its state code and timers only: it moves by the client's
`ServerMove`s. Anything else ticks as a standalone game's; a viewport's own
player is spawned with the remote role simulated (`UGameEngine::Init`,
`LoadMap`), a client's with autonomous.

### The native lists

Each is its class's replication statements written in C++ (Engine.dll,
2026-09-27): a value goes when it differs from what the client last got
and the condition holds, all only on the server (`Role` the authority).
`Mover` (`0x10365320`), `ZoneInfo` (`0x103657a0`) and `GameReplicationInfo`
(`0x10366960`) are their statements exactly. The others differ:

- **`Actor`** (`0x103618c0`): `SimAnim`, `AnimMinRate` and `bAnimNotify` go
  with `AnimSequence` -- a mesh, and a remote role up to simulated proxy
  unless owned with `bClientAnim`, or a demo recording --, UE1's statement;
  Deus Ex's script gives `SimAnim` and `AnimMinRate` below simulated proxy
  and `bAnimNotify` at it. The blended animations its script added
  (`BlendAnimSequence`, `SimBlendAnim`, `BlendAnimMinRate`) are in no list and
  never go.
- **`Pawn`** (`0x10363bc0`): `PlayerRestartState` is in no list and never
  goes, though its statement names it for the owner.
- **`PlayerPawn`** (`0x103649d0`): the owner's list also names
  `bNeverAutoSwitch`, which no statement names -- so it has no replication
  index, and its change sends whatever has the first.
- **`PlayerReplicationInfo`** (`0x10365ca0`): `Actor`'s list only in the
  first bunch (`bNetInitial`).
- **`Inventory`** (`0x10367450`): an always-relevant item past its first
  bunch sends `bHidden` alone; and one not owned by the client, a simulated
  proxy with an `AmbientSound`, sends its `Location` too.

## Deus Ex's additions

- **`Actor.RelevantRadius`:** a viewer with one takes every pawn inside it as
  relevant, seen or not.
- **`PlayerPawn.AdditionalViews[3]`:** more viewpoints for relevancy, of which
  only the first works.
- **The client's classes checked** (the game's script, `DeusEx.u`): a joined
  player's pawn is called to check its console's class and its root
  window's -- `VerifyConsole(Engine.Console)`,
  `VerifyRootWindow(DeusEx.DeusExRootWindow)`, exact classes, no subclass
  --, and one that fails tells the server's game, which calls back
  `ForceDisconnect("Invalid Console class, disconnecting")` (or `RootWindow`):
  the line added to the console, then `DisconnectPlayer`. Every server with
  a `DeusExGameInfo` game does it, the modded ones too.

## The database

The functions above are in `Engine.dll`'s database
([its database](engine-dll.md#the-database)), each with a one-line comment;
the pending level's handler, the relevancy test, the priority and its sort
are named there by hand.
