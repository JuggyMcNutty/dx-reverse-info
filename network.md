# The network

How the original plays over a network. `Engine.dll` holds the protocol:
connections, channels, replication and the joining handshake. The sockets under
it, the script's links and the master server are `IpDrv.dll`'s
([`IpDrv.dll`](ipdrv-dll.md)).

Deus Ex's network code is Unreal Tournament's of its day (native replication
lists and the world-stats challenge among it), engine version 1100, with three
Deus Ex additions ([below](#deus-exs-additions)): two in `Engine.dll`, one in
the game's script. A client that joins the game's servers speaks this protocol
to the bit.

## The parts

- **The net driver** (`UNetDriver`; on the internet `IpDrv.dll`'s
  `TcpNetDriver`, over UDP) listens as a server or connects as a client, and
  ticks its connections: packets in first (`TickDispatch`, `0x10409670`), out
  last (`TickFlush`, `0x10409570`).
- **A connection** (`UNetConnection`) carries up to 1,023 channels: the control
  channel (0), carrying the handshake as text; one per actor the other side is
  told of; file channels, for downloads.
- **The level** (`ULevel`) is the driver's listener. It accepts or refuses
  connections (`NotifyAcceptingConnection`, `0x1039ee60`: a new client's
  packets ignored while the server travels) and channels
  (`NotifyAcceptingChannel`, `0x1039f290`: a server takes the control channel
  and file channels a client opens, a client only
  actor channels), and answers the handshake.
- **Demos** (`UDemoRecDriver`) write the packets a level sends a client to a file, and play
  them back as a client's level ([demos](#demos)).
- **The settings**, `[IpDrv.TcpNetDriver]` in `DeusEx.ini` (the GOG build's):
  `ConnectionTimeout` 15 s, `InitialConnectTimeout` 500 s, `AckTimeout` 1 s,
  `KeepAliveTime` 1 s, `MaxClientRate` 20,000 bytes/s, `RelevantTimeout` 5 s,
  `SpawnPrioritySeconds` 1, `ServerTravelPause` 4 s, `NetServerMaxTickRate` 20,
  `LanServerMaxTickRate` 35, `StaticUpdateRate` 12, `DynamicUpdateRate` 40,
  `AllowDownloads`.

## Joining

A server listens once a map is opened with `?listen` (`ULevel::Listen`,
`0x1039e7c0`):

- the net driver `[Engine.Engine]`'s `NetworkDevice` names binds the URL's port,
  before the game's `InitGame`, which sees a listen server (dedicated without a
  client);
- the game engine's `ServerActors` are spawned, from the section of the class
  `[Engine.Engine]`'s `GameEngine` names (`[DeusEx.DeusExGameEngine]`), each a
  class and then `Key=Value` settings of its config properties: the LAN beacon
  (`IpDrv.UdpBeacon`, answering `REPORT` and `REPORTQUERY` on port 8,777), the
  query answerer (`IpServer.UdpServerQuery`: GameSpy's `\basic\`, `\info\`,
  `\rules\` and `\players\` on the first free port after the game's), and the
  master servers' uplinks (`IpServer.UdpServerUplink`, which announce the server
  only with `DoUplink` set:
  [the master server](ipdrv-dll.md#the-master-server));
- the level's `NextSwitchCountdown` is set to `ServerTravelPause`.

The level's `EngineVersion` and `MinNetVersion`, which the query answerer
reports and the Join screens compare, are Deus Ex's 1100; its `ComputerName` is
the machine's (Windows' computer name).

The control channel carries lines of text: the server's side is
`ULevel::NotifyReceivedText` (`0x1039f780`), the client's the pending level's
(`UNetPendingLevel`, `0x1040a880`). A line's command is Core's `ParseCommand`'s
(`0x10147a20`): past any spaces and tabs, the word in any case with no ASCII
letter or digit straight after it, the rest of the line past the spaces and
tabs after it, so `<tab>FAILURE<tab><tab>text` is a `FAILURE` of `text`. Each
`KEY=` value is its `Parse`'s, as the command line's
([`cli-flags.md`](cli-flags.md)): a key in any case, but not straight after a
letter or digit, so `HELLO`'s `VER=` is not `MINVER=`'s. A text value is in
double quotes, or up to a space, tab, CR, LF or comma, so a login's
`Name=JC(1)` comes whole; `URL=` holds 1,023 characters, `PKG=` 63, `LEVEL=`
4,095 (`Parse`'s `FString` form, `0x10146dc0`). A number is `Parse`'s int
form, `appAtoi` of what follows, so `VER= 1100` is 1100, `FLAGS=` its DWORD
form, `wcstoul`'s (`0x10147270`); `LONE=` is true for `On`, `True` or `1`
alone (`ParseUBOOL`). A `GUID=` is `Parse`'s GUID form (`0x101478e0`): its
text into 256 characters, then four words of 0, and where the text is 32
characters long each word the base-16 `wcstoul` of its eight (`appStrtoi`,
`0x101235e0`), the last eight the last word; a `USES` line without one keeps
its package's 0 (`FPackageInfo`, `0x1012b8b0`). What the client does with it
-- the cache's name, the file asked for, `HAVE` -- is the words, written back
as `%08X` each, never the server's text. A line goes in one reliable bunch
of 4,015 bits at most (`FOutBunch`, `0x103fa3b0`: a packet's 512 bytes less
81 bits), and one longer is not sent, `Control channel bunch overflowed`
logged (`UControlChannel::Serialize`, `0x103fc6f0`): some 498 characters of
8-bit text, so `URL=`'s and `LEVEL=`'s limits are never reached.

1. **Client:** `HELLO REVISION=0 MINVER=1100 VER=1100`.
2. **Server:** `UPGRADE MINVER=1100 VER=1100`, and the connection closed, when
   the client's `VER` is below 1100 or its `MINVER` above (a missing one counts
   as 219). Otherwise `CHALLENGE VER=` (the lower of the two versions)
   `CHALLENGE=` (a number from the CPU's clock) `STATS=` (whether the game logs
   world stats).
3. **Client:**
   - `NETSPEED` and its rate in bytes/s: `[Engine.Player]`'s
     `ConfiguredInternetSpeed` (2,600 in the GOG build's ini), or its
     `ConfiguredLanSpeed` (20,000) with `?LAN` in the URL, as the Join LAN
     screen adds;
   - `LOGIN RESPONSE=` (the engine's answer to the challenge) `URL=` and the
     travel URL's own text (`FURL::String`, `0x103f9210`) without the server's
     address or a `game=` option (`0x1040b4dd`), a port not the default's kept
     before the map -- `:7791/Index.dx?...`, which a server reads as the map
     `:7791` and the portal `Index.dx` (DXEngine's harness's `PortJoinConsole`)
     --: the map (the default one when the address named none) and its options (`Name`, `Class`,
     `Team`, `Skin`, `Face`, `OverrideClass`, `PASSWORD`: those the player has;
     from the game's `User.ini`, whose `[DefaultPlayer]` holds `Name` and
     `Class`, a login carries only those);
   - with stats on (`STATS=1`: the server's game's `bWorldLog`), `Checksum=`:
     the MD5 of the viewport player's `PlayerReplicationInfo.PlayerName` then
     its `ngWorldSecret`, each as UTF-16 without the terminator, in 32 lowercase
     hex digits; `Checksum=NoChecksum` when the password is empty. Without
     stats, nothing (`0x1040a880`).
4. **Server:** a `LOGIN` with no `RESPONSE=`, or with one that is 1 where
   the challenge's answer is 0 and 0 where it is anything else, gets
   `FAILURE CHALLENGE` (`0x1039fffe`): the server compares the response with
   whether the answer is 0, not with the answer (`0x1039fb7c` to
   `0x1039fb90`), so in practice a response of 0 alone is refused, any other
   let on, the right one or not. Then the game's `PreLogin`
   (script) may refuse, by its error alone (`0x1039f780`: a
   `FailCode` with no error lets the login on): `FAILURE` and its message,
   `FAILCODE` and its code (the client's menu takes it: a password asked for,
   the join's error staying the FAILURE's, `0x1040a880`), and the connection
   closed. Otherwise `WelcomePlayer` (`0x1039f500`) sends:
   - a `USES GUID= PKG= FLAGS= SIZE= GEN=` line per package of the server's
     list, made as the map opened (`UGameEngine::BuildServerMasterMap`,
     `0x10388b10`): the map's own; each of the `ServerPackages` in the game
     engine's section (none in the GOG build's ini; each logged
     `Server Package: <name>`); the package of the game's class. Each is
     followed by what it imports, depth first (each package's imports, in its
     import table's order, straight after it). None twice, and none flagged
     server-side only (Deus Ex's `IpDrv`, `IpServer`, `UWindow`, `UBrowser`);
   - `WELCOME LEVEL=` (the map) `LONE=` (`bLonePlayer`), whose `CHALLENGE=`,
     if a server gives one, the client takes as the connection's challenge
     (`0x1040a880`);
   - `STATICRATE` and `DYNAMICRATE` from the settings.
5. **Client:** each package it lacks downloaded, one at a time
   ([downloads](#downloads)), one whose `<name>.dll` is in the game's System
   folder counting as had (`0x1040a880`; `handshakeserver.py --pkg Window`).
   With all in hand, the map loaded (below), then
   `HAVE GUID= GEN=` for each package whose generation here differs from the
   server's `GEN=` (the server takes the number as it is, `0x1039f780`, and
   counts only what the client's has), one frame
   drawn ([what the player sees](#what-the-player-sees-of-a-join)), and `JOIN`,
   not in a single player's game (`LONE=1`). `NETSPEED` again whenever the
   player sets one (the server takes one of at least 500, held to
   `MaxClientRate`). The rate is the connection's `CurrentNetSpeed`, which the
   game's script reads as `Player.CurrentNetSpeed`: the connection is the
   player (`UNetConnection` is a `UPlayer`), so `PlayerPawn.ServerMove` checks a
   client's place at most every 180 / that rate seconds. Until the client's
   `NETSPEED`, a server's connection has the server's own `[Engine.Player]`
   `ConfiguredInternetSpeed`, or `ConfiguredLanSpeed` with `?LAN` in its URL
   (`0x10401490`).
6. **Server:** spawns the player (`SpawnPlayActor`, the game's `Login`, as an
   autonomous proxy), or answers `FAILURE` and the reason, a bare `FAILURE `
   when the game gives none, logging `join failure` (`0x1039f780`). The `JOIN` is taken
   whenever the connection has no player yet, whatever came before it: a
   `HELLO` and a `JOIN` log a player in with no challenge answered and no
   `PreLogin` asked (`0x1039f780`).

A client refused (`FAILURE`) or told `UPGRADE` stays in the level it was in,
shown why ([what the player sees](#what-the-player-sees-of-a-join)). A
`FAILCODE` goes to the console's `ConnectFailure` with the URL less its
password, for the menu to ask again. `USERFLAG` sets a number of the
connection's either way. The client keeps `DYNAMICRATE` and `STATICRATE` each as
a time between updates (1 s / the rate, held to 0.01..1 s; none for 0), which
Deus Ex's `ReplicateMove` paces the player's moves by.

- **The client's level** (`UGameEngine::LoadMap`): loaded as a client's
  (`NetMode` 3). Of the map's actors it keeps the static and no-delete ones,
  each with `Role` and `RemoteRole` exchanged, and destroys the rest (the server
  sends them). No `GameInfo`, no `InitGame`; the begin-play events as a
  standalone level's. Before it loads, the level being left paints one
  `CONNECTING` frame ([the loading screen](engine-dll.md#the-loading-screen)).
  Until its player arrives, the level and the Entry level show `LevelAction`
  Connecting (`UGameEngine::Tick`).
- **The player** (`HandleClientPlayer`, `0x10405290`): the first bunch of a
  `PlayerPawn` the client owns (below), while the connection is still pending,
  makes it the client's: the viewport takes the connection's speed and the two
  update intervals; the pawn becomes an autonomous proxy with the view's show
  flags and render map set, possessed by the viewport (`SetPlayer`, and
  `Possess`); input reset; `LevelAction` back to none; the connection open.

## Downloads

**Which** (the client's `WELCOME`, `UNetPendingLevel::NotifyReceivedText`): each
`USES` package is looked for with its GUID
([a package's file](core-dll.md#packages-and-linkers)): on the paths by its
name, else in the cache by its GUID. One not found, with no `<name>.dll` either,
is needed (`PKG_Need`, `0x8000`, added to its flags). One needed while the
client's `AllowDownloads` is off, or whose `FLAGS` lack `AllowDownload` (`0x1`),
ends the join: `Downloading '<name>' not allowed`, the connection closed.
Otherwise the first needed one is asked for and the join counts as welcomed; its
map loads when none is needed any more. A file found whose GUID is not the
server's (a same-named package on the paths) fails the join as the map loads:
`Package '<name>' version mismatch` (Core's `PackageVersion`).

**Asking** (`UNetConnection::ReceiveFile`, `0x10405490`): a file channel (type
3), named after the package, and in one reliable bunch the GUID's four words.
With no channel free, the download fails with `ChAllocate`.

**Sending** (`UFileChannel::ReceivedBunch`, `0x103ffff0`, a server's side):

- the GUID is looked up in the connection's package list among the packages
  flagged `AllowDownload`, the only ones whose file is known (`FPackageInfo`'s
  `URL`); the level is asked (`NotifySendingFile`: a server's lets its clients
  have any, `Client requested file: Allowed`; a client's refuses a server); the
  file is opened, logged `Sending '<file>'` (`NetSend`);
- anything else is logged `Received invalid file request` (`NetInvalid`) and
  answered with an empty, unreliable bunch that closes the channel
  (`0x10400464`): lost, it leaves the client's download waiting, the server's
  channel closing for the connection's life and a later request on its index
  passed over;
- then each tick (`UFileChannel::Tick`, `0x10400780`), while the channel's
  reliable buffer has room (the rate left out: `IsNetReady(1)`), a reliable
  bunch of as much of the file as the packet has room for (`MaxSendBytes`: the
  packet's bits less its header, its trailer and a bunch header's 64, in bytes),
  the packet sent after each. The bunch that ends the file closes the channel.

A file channel on either side has its connection send a packet every tick
(`TimeSensitive`), so the client's acks keep the server's buffer draining.

**Receiving** (the same functions, a client's side): the first bunch opens a
temporary file in `CachePath`, the folder made first
([the cache's files](core-dll.md#packages-and-linkers)), logged
`Receiving package '<name>'`. Each bunch's bytes go into it, and the player is
shown `Receiving '<name>' (F10 Cancels)` and `Size <n>K, Complete <n>%` for 4 s
(`Engine.int`'s `ReceiveFile` and `ReceiveSize`; the size the `USES` line's). A
failed open or write closes the channel with `NetOpen` or `NetWrite`. When the
channel goes (`UFileChannel::Destroy`, `0x10400a40`):

- nothing received is `Server refused to send '<name>'` (`NetRefused`);
- a size other than the `USES` line's is `NetSize`, a failed move `NetMove`;
- else the file is moved to `<CachePath>\<GUID>.uxx` (that extension written in,
  not `CacheExt`), and the player is shown `Success` and `Received '<name>'`.

The pending level is told either way (`NotifyReceivedFile`, `0x1040bda0`): an
error fails the join (`Downloading package '<name>' failed: <error>`, the first
error kept); a success clears the package's `PKG_Need` and asks for the next. A
failed download's temporary file is left for the cache's next cleaning.

**Going** (`UGameEngine::LoadMap`, `0x1038c1f0`): a package stays loaded while
anything uses it, and a map load collects the garbage once the new map is in
([the map load's collection](engine-dll.md#the-map-loads-collection)). So a
server's downloads go at the next map that does not use them (the menu's map
after a `DISCONNECT`), and another server's package of that name loads in their
place. Its version is checked as the map loads, before that collection
(`GetPackageLinker`'s GUID), so joining that other server straight from the
first one's level, or from the Entry level a lost server left, finds the old
version still loaded: `Package '<name>' version mismatch`.

## What the player sees of a join

`UGameEngine::SetProgress` (`0x10389e00`) sets the first viewport's player's
`ProgressMessage[0]` and `[1]`, their `ProgressColor`s white, and
`ProgressTimeOut` to the level's time plus the seconds given; -1 s calls the
player's `ShowUpgradeMenu` first. The console's `Tick` calls the player's
`ShowProgress` while that time is ahead: Deus Ex's opens
`MultiplayerMessageWin`, which draws the two lines centred in blue and sends
`CANCEL` for F10.

- **Connecting.** While a join is pending, each frame drawn
  (`UpdateConnectingMessage`, `0x10388900`, from `UGameEngine::Draw`): when
  the first viewport's player shows no progress, its `ProgressTimeOut` behind
  its own level's time (`0x1038895f`: Entry's for a player in the Entry
  level), `Connecting (F10 Cancels):` and `deusex://<host>/<map>`
  (`ConnectingText`, `ConnectingURL`) for 60 s. The frame that loads the
  join's map draws once more before its `JOIN` goes, the join still pending
  ([the game engine's frame](engine-dll.md#a-levels-tick)): so the player
  just logged in to the Entry level to wait for its pawn, a new one with no
  progress of its own, is given the lines there, and the console's tick in
  the same draw opens `MultiplayerMessageWin` for them; they stay through
  the wait, the pending level gone.
- **Failing.** A pending level with an error (`UGameEngine::Tick`,
  `0x1038fe90`): `Connection failed` and the error for 4 s, logged
  `Pending connect to '<url>' failed; <error>`, and the pending level deleted;
  the level plays on. Its own tick (`0x1040c170`) makes a closed connection's
  error `Connection failed`; a map failing to load as the client's shows the
  same with the load's error. A browse to a server cancels a join already
  pending.
  - The server's `FAILURE`: first `Rejected By Server` and its text for 10 s,
    the error `Rejected By Server: <text>`, the connection closed.
  - `UPGRADE` with a `MINVER` of 1,100 or less (a missing one counts as 0
    here): `Connection failed` and `Server's version is outdated` for 6 s;
    above, the upgrade menu, `SetProgress`'s -1 s: the player's
    `ShowUpgradeMenu`, which `PlayerPawn` leaves empty and no Deus Ex class
    fills. Nothing else: no error and no close (`0x1040a908` to
    `0x1040a9c3`). The server closed its side, which sends nothing more,
    a closed connection's channels closing silently (`UChannel::Close`,
    `0x103fa800`), and the client's later packets open it a new connection
    that answers them ([the net driver](ipdrv-dll.md#the-net-driver)): so
    the join stays pending, its `Connecting` lines back once those run out,
    until the player cancels it, another join replaces it, or no packet
    comes for `InitialConnectTimeout`.
  - No net driver for the URL (`UGameEngine::Browse`, `0x1038ad30`):
    `Networking Failed` and the error for 6 s.
- **Lost.** A client level whose server connection closes
  (`ULevel::TickNetClient`, `0x103a2f10`; the browse at `0x103a3030`), or which
  the server sends `FAILURE` after the join (`ULevel::NotifyReceivedText`),
  browses `?failed` (`?entry` alike, less the message). `Browse` logs
  `Failed; returning to Entry`, drops the level's net driver, makes the Entry
  level the one played with no level action, and spawns a player there for each
  viewport; with no join pending, `Connection failed` shows for 6 s. The next
  map's load destroys that player, as it does each viewport's actor where it
  stands.
- **The game engine's commands** (`UGameEngine::Exec`, `0x1038a030`):
  - `CANCEL`: with a join pending, `Cancelled Connect Attempt` for 2 s, else the
    progress cleared; then the pending level deleted (`CancelPending`,
    `0x1038ac50`);
  - `DISCONNECT`: travel to `dx.dx` (Deus Ex's `DeusExPlayer.DisconnectPlayer`
    sends it: the menu's disconnect, and the game's `ForceDisconnect`);
  - `RECONNECT`: travel to the last URL.
- **The viewport's** (`UViewport::Exec`, `0x10373a60`): `NETSPEED <rate>` keeps
  the rate as `[Engine.Player]`'s `ConfiguredInternetSpeed` (saved); on a server
  joined without `?LAN`, with a rate of 500 or more, it sets the connection's
  speed, held to the driver's `MaxClientRate`, and the viewport's, and sends
  `NETSPEED <rate>`. `LANSPEED` does the same for a `?LAN` server, and keeps its
  rate as `ConfiguredInternetSpeed` too, the field `NETSPEED` writes (the
  connection takes `ConfiguredLanSpeed`, the next one, for `?LAN`).
- **The connection's** (`UNetConnection::Exec`, `0x10401c50`, its `this` the
  connection's `FExec` part, 0x2C in): `GETPING`
  answers a float of the connection times 1000 as an int and `GETLOSS`
  another float as an int, each after a blank (`" %i"`), which
  `DeusExServerPing` strips -- its lag, the stats period's mean of each
  ack's round trip less half the connection's last frame time, no least kept
  (`0x10403240`-`0x10403261`, set each period `0x10404dc6`-`0x10404deb`;
  9999 s as the connection is made, `0x104015f8`, so ` 9999000` until its
  first period ends -- the 1 s at `0x104015ee` is the period's length), the
  sum begun at 9999 as the connection is made (`0x10401604`). The frame
  time is the machine's clock's, `appSeconds` (the time-stamp counter's
  seconds since the machine started), between the connection's last two
  ticks, its last time 0 as the connection is made (`0x10404bb8`-
  `0x10404c69`; the constructor, `0x10401490`, sets none of it), so its
  first frame time is the clock's whole count, and each ack taken before
  the connection's second tick -- on a server the client's answer to the
  `CHALLENGE` -- loses half of it: the first period's lag is 9999 s less
  half the machine's uptime over its acks' count, below 0 on a machine up
  more than twice 9999 s (-194 s on one up 12 hours, DXEngine's
  `AlertServer`), hundreds of seconds on one up less. The first second's
  average frame time is that count too, which a client's local
  `PlayerReplicationInfo.Ping` loses half of (`PostNetReceive`,
  `0x103689b7`); and its incoming packet
  loss in percent, of those lost and the packets a second come in (100 ×
  lost / (lost + packets a second), the sum at least 1), the outgoing, 100 ×
  lost / the packets a second sent, kept beside it -- then
  `UPlayer::Exec`. A pawn's `ConsoleCommand` goes to its own player
  (`APlayerPawn::execConsoleCommand`, `0x103ba200`): on a server a remote
  player's connection answers so, which `PlayerReplicationInfo.Timer` takes
  for its ping; a local player's viewport answers `GETPING` with `0` and
  takes no `GETLOSS` (`UViewport::Exec`, `0x10373aee`; `WordsServer`).
  Each period also sets the player's `bBadConnectionAlert`, which no stock
  script reads: on while the player has its channel and its lag plus 1.2 s
  for all lost of the greater loss passes 0.8 s, or the rate the loss leaves
  falls under 2,000 bytes a second; on too while fewer than 2 packets a
  second come in (`0x10404e1c`-`0x10404ef0`). A client that joins within
  its connection's first second (DXEngine's, its map loaded in some 0.2 s;
  the original's within 0.95 s) has the first period end with its player
  in: on a machine up more than twice 9999 s its lag is below 0 and no
  alert is set, on one up less it is on until the next period (DXEngine's
  harness's `AlertServer`: off from the player's first half second in the
  game, `GETPING` ` 9999000` at the join, then below 0).

## Server travel

A server moves its game to another map, and its clients follow:

1. **The level's `ServerTravel(URL, bItems)`** (script; the game engine's
   `SERVERTRAVEL <url>` calls it, and a game's own map change): Deus Ex's does
   nothing in a standalone game. Otherwise, unless a travel is already set,
   `NextURL` and `bNextItems` are set and the game's `ProcessServerTravel` runs
   (with no game, `NextSwitchCountdown` 0).
2. **`GameInfo.ProcessServerTravel`** (script):
   `ClientTravel(URL, TRAVEL_Relative, bItems)` to each remote player's pawn (a
   replicated call); `PreClientTravel` for the host's own, whose `Skin`, `Face`,
   `Team`, `Name` and `Class` a listen server appends to `NextURL`. A game that
   is not networked switches at once (countdown 0).
3. **The server** refuses no one but takes no one new while `NextURL` is set:
   `NotifyAcceptingConnection` ignores a new client's packets
   (`Server <level> refused`). Once `NextSwitchCountdown` runs out (the
   `ServerTravelPause` 4 s it was given when the map began listening;
   `UGameEngine::Tick`): `Server switch level: <url>`; the players' travel info
   taken when `bNextItems` is set; a browse to `NextURL` relative to the last
   URL, whose options (`?listen`, the game) it keeps. The old net driver goes
   with its level, closing the clients' connections, and the new map listens
   again.
4. **A client**: the `ClientTravel` browses relative to its last URL (the
   server's address, the next map): a new join that the server ignores until it
   listens again, the handshake's first packets sent again meanwhile. When the
   old level's connection closes, the client browses `?failed` and goes to its
   Entry level (`Failed; returning to Entry`), showing no failure while the join
   is pending; the join then loads the next map. The `?failed` is the
   viewport's next travel, absolute (`ULevel::TickNetClient`, `0x103a2f10`),
   so it takes the last URL's player options --
   `Index.dx?failed?Name=Player?Class=DeusEx.JCDentonMale` -- and the player
   logs in on Entry with them.

## Addresses

A URL starts as the default one, `[URL]`'s (`FURL::StaticInit`, `0x103f6c50`:
the protocol `deusex`, no host, the port 7,790, the map `Index.dx`, no portal),
and its text is read in this order, its first 1,023 characters alone, which
it copies (`appStrncpy` into 1,024, `0x103f7d00`-`0x103f7d16`), past its leading
spaces (its trailing ones stay in the map) (the URL parser, `0x103f7b60`):

- the options (`?`) and a portal (`#`) first, each up to the next `?` or `#`,
  in any order; a space in one makes no URL;
- a `:` as the second character makes it a file (a drive letter): all of it
  the map, at the default protocol and portal, with no host;
- else a `:` further on, before any `.`, ends a protocol;
- `//` may come before the host; a `/` there alone makes no URL;
- the host is the text up to a `/`, when it has a `.` past its first character
  not followed by the map's or a save's extension (`dx`, `dxs`); the map is
  then the default one, none for another protocol;
- after a `:` in the host comes the port (`appAtoi`), the default without one;
- after the `/` comes the map; for the game's protocol, in any case
  (`FURL::IsInternal`, `0x103f97b0`), a `/` in it marks a portal, up to a
  second `/`, past which anything makes no URL:
  `open 01_NYC_UNATCOIsland/tunnel_drop_nyc` is that map at that portal;
- a space in the protocol, host or portal makes no URL either, and so does
  no host, no map of the game's protocol and no option.

A URL that is none is the default one, marked invalid. `HasOption` matches a
whole option, in any case (`0x103f9df0`): `?listen=1` is not `?listen`;
`GetOption` an option's start (`0x103f9ee0`), asked with its `=`.

Built on a base, as a travel builds it: a relative travel's URL takes the
base's protocol, host, map, portal and port, a relative or partial one the
base's options but `PUSH`, `POP`, `PEER` and a bare `LOAD` (any case), and the
text's over them, each where it names one: a relative one naming a host
without a port keeps the base's; a partial travel, the console's `open`, keeps
the player's options and none of the server. An absolute one of the game's
protocol takes the base's player options it lacks or has empty -- `Name=`,
`Team=`, `Class=`, `Skin=`, `Face=`, `Voice=`, `OverrideClass=` (any case) --,
after its own, each logged (`URL: Adding default option Name=Player`): the
console's `start`, a hosted game's, keeps the player's name.

As text (`FURL::String`, `0x103f9210`): the protocol and `:` only when it is not
the default, in any case (or the URL is asked whole), `//` after them with a
host; the host when it, or the port, is not the default, then `:port` only for
a port not the default, then `/`; the map; `?` and each option; `#` and the
portal when there is one.

A travel to a URL that is none (`open DX.dx?Name=Two Words`): the game
engine's browse (`0x1038ad30`) logs `Browse: Index.dx` and refuses it,
`Invalid URL: Index.dx`, an error the travel's tick drops; Deus Ex's browse
goes on with its map all the same
([the game engine](deusex-dll.md#the-game-engine-travel-and-saving)):
`Index.dx`, outside any mission, is not there, so `Current` is emptied and the
level's own map is loaded again on that URL, with no option, the player
logging in with no name (`Player`). A start URL that is none is fatal
(`UGameEngine::Init`, `0x103891c0`: `Invalid URL: <url>`).

A URL that is one, past `?failed`, `?entry` and `?pop`: the game engine's browse
leaves `?restart`, a `?load=` or `?loadgame=` (`GetOption`, any value) and a map
of the game's protocol with no host to Deus Ex's browse, failing
(`0x1038b5d7`-`0x1038b6e0`; [the game
engine](deusex-dll.md#the-game-engine-travel-and-saving)); with a client, one of
the game's protocol with a host is joined; one of another protocol is handed to
the system: `appLaunchURL` (Core.dll `0x1016c770`) logs `LaunchURL <url> ` and
opens it with `ShellExecute`'s `open`, the error, when that fails,
`Failed launching URL`, and the browse fails, the level playing on
(`0x1038b85f`-`0x1038b890`). Any server's `ClientTravel` reaches it: a server
can have its clients' systems open any URL, of any protocol's handler.

The Join screens join with the console's `open` and the address typed or picked
(Join LAN adds `?lan`).

**The level's URL and the last URL.** `LoadMap` gives the level the URL it
loads (the level's `URL`), but for a URL with an option starting `load` --
`?loadonly`, `?loadgame`, `?load=`, as `FURL::GetOption` (`0x103f9ee0`)
matches an option's start --, which leaves the level the URL it holds: a
level's file keeps one (`ULevel::Serialize`), every stock map's the default
protocol, `Index.dx` and port 7790, so a restarted level's reads `Index.dx`,
and a save's the URL its level was entered by. A server listens before its
level begins play (`ULevel::Listen`, `0x1039e7c0`): the net driver writes the
address and port it bound into that URL
([`IpDrv.dll`](ipdrv-dll.md#the-net-driver)). At the end `LoadMap` keeps the
URL as it was given, with no host, as the game engine's last URL
(`UGameEngine` + 0x74, `0x1038e05c`), once the level has begun play and the
player has logged in; Deus Ex's browse then makes a level's own URL the last
URL where the level came from `Current` or a save
([the game engine](deusex-dll.md#the-game-engine-travel-and-saving)). The
last URL is what a travel is relative to -- the server's (`?RESTART` too) and
a client's (`Tick`, `0x1038fe90`) -- and what the console's `open` and
`start` build on and `reconnect` opens again (`Exec`, `0x1038a030`). So a
server never travels to its own address. Before a viewport's travel `Tick`
takes every `loadonly` option (the whole option, any case) and the portal off
the last URL, in place: the travel after a restart carries no `?loadonly`.

The scripts' own addresses:

- **`PlayerPawn.GetPlayerNetworkAddress()`** (`0x103df310`): for a pawn whose
  `Player` is a net connection -- a remote player's, on the server -- that
  connection's address, `a.b.c.d:port` (`LowLevelGetRemoteAddress`,
  [`IpDrv.dll`](ipdrv-dll.md#the-net-driver)); for any other, the host's own
  player included, "". An admin's `KickBan` bans what comes before its `:`.
- **`GameInfo.GetNetworkNumber()`** (`0x103e69d0`): the address the level's
  net driver is bound to (`LowLevelGetNetworkNumber`): `0.0.0.0` but with
  `MULTIHOME=` or `-PRIMARYNET`. "" with no net driver. `StatLog` writes it in
  the server's info.
- **`LevelInfo.GetLocalURL()`** (`0x103df900`): the level's URL as text: a
  listen server's `0.0.0.0/DXMP_Cathedral?...` (its port the default, 7790).
- **`LevelInfo.GetAddressURL()`** (`0x103dfa90`): the level's URL's host and
  port, `host:port`: a listen server's `0.0.0.0:7790`.
- **`Actor.GetURLMap()`** (`0x103b8df0`): the last URL's map, the game
  engine's (the level's engine + 0x90), not the level's own: after a load of
  a URL with an option starting `load` from `Maps`, the map that URL named,
  where the level's URL is its file's `Index.dx` (DXEngine's
  `URLEdgesConsole`: `01_NYC_UNATCOHQ` and a URL of 8 characters after
  `open 01_NYC_UNATCOHQ?load=9`). While a map loads, its level beginning
  play and its player logging in, it is still the last level's. The
  multiplayer map lists (`MapList`, `DXMapList`) find the map played by it.
- **`PlayerPawn.UpdateURL(NewOption, NewValue, bSaveDefault)`** (`0x103b87c0`):
  `NewOption=NewValue` into the last URL's options, in place of one of that
  name (`FURL::AddOption`, `0x103f9960`, any case); with `bSaveDefault` written
  to `[DefaultPlayer]` in the user ini as well.
- **The player's options in the URL** (`FURL::LoadURLConfig`, `0x103f9bc0`):
  every key of the user ini's `[DefaultPlayer]`, in its order and as the ini
  spells it, each `Key=value` an option through `AddOption` (`0x103f9960`),
  which takes the place of an option that matches it up to and with its `=`,
  in any case, so a key given twice is one option with the last value (the
  config cache hands the section over whole), and a line with no name, `=x`,
  is the option `=x`, in the place of any other that begins with `=`. The
  game engine's first URL takes them (`UGameEngine::Init`, `0x103891c0`), and
  so does `PlayerPawn.GetDefaultURL(Option)` (`0x103b8a90`), which answers
  the text after `Option=` of the first of them that begins so
  (`FURL::GetOption`, `0x103f9ee0`), "" with none: `GetDefaultURL("")` is the
  line with no name's value. A client's `LoadMap` (`0x1038c1f0`) writes
  seven of its URL's options back there, each the URL has (`SaveURLConfig`,
  `0x103f9cb0`): `Name`, `Team`, `Class`, `Skin`, `Face`, `Voice`,
  `OverrideClass`.

## Packets

UDP datagrams of bits, first bit lowest. A number with a known maximum takes as
many bits as the maximum needs (`FBitWriter::WriteInt`).

- **A packet** (`UNetConnection::ReceivedPacket`, `0x10402fe0`): its number, 14
  bits (counting round 16,384); then acks and bunches; then a 1 bit and 0s to
  the byte, so the receiver finds the end from the last byte.
- **An ack:** a 1 bit and the number of a packet received (14 bits). A packet
  number the acks skip is taken as lost.
- **A bunch** (`SendRawBunch`, `0x104044d0`): a 0 bit; a control bit, then open
  and close bits if it is set; a reliable bit; the channel's index, 10 bits; if
  reliable, the channel's own count of reliable bunches, 10 bits (round 1,024);
  if reliable or opening, the channel's type, 3 bits (1 control, 2 actor, 3
  file); the data's length in bits, up to the packet's size; the data.
- **Reliable bunches** are delivered in order: up to 128 wait for a gap to fill
  (`ReceivedRawBunch`, `0x103fb230`), duplicates are dropped, and a lost one is
  sent again.
- **Merging** (`UChannel::SendBunch`, `0x103fb6b0`): a channel's bunch goes into
  the last one sent, one header for both, when that one is the same channel's
  and still ends the packet being built (no ack written since, which `SendAck`
  stops, and no `FlushNet`), and the two fit the packet with 9 bytes to spare
  (`0x103fb7f9`); a
  reliable one keeps its record and sequence number. Actor updates, text and
  remote calls may merge; a file's bunches and a channel's close never do.
- **Acks:** a packet is acknowledged as soon as its number is read, before its
  bunches; each acknowledgement goes again with the next packet's first new one.
- **The first bunches:** until the control channel's open is acknowledged, its
  unacknowledged bunches go again every second (`UChannel::Tick`, `0x103fae80`):
  a client's `HELLO` while the server comes up.
- **A reliable bunch** already had is dropped. An unreliable one is taken only
  if it opens its channel and closes it too -- an actor sent once, to keep
  (`bNetTemporary`) -- or once the channel's open has come; any other is
  dropped, the connection playing on ("Received unreliable bunch before open",
  `0x1040372c`-`0x10403759`), so an actor whose open was lost has its updates
  wait for the open's resend (DXEngine's harness's `OpenLossServer` behind
  `netdrop.py`). A channel the other side opens is open and acknowledged here
  from its opening bunch, whose packet it keeps as its open's. Before the
  control channel is open, a bunch for a channel not open, but the control
  channel's own open, ends the packet, nothing more of it read ("Received
  bunch before connected", `0x104035d9`): a first packet whose first bunch is
  an actor channel's has its `HELLO` passed over, its acks alone answered
  (`bunchfirst.py`).
- **Timing:** a packet goes out at the end of a tick that sent a bunch;
  otherwise, with the acks' second copies (written every tick), when nothing has
  gone for `KeepAliveTime`. A connection with nothing in for `ConnectionTimeout`
  (`InitialConnectTimeout` until it is open and its player in; a server's
  connection is open from a client's first packet,
  [`UTcpNetDriver::TickDispatch`](ipdrv-dll.md#the-net-driver)) closes
  (`Tick`, `0x10404a40`).
  Sending stops for the tick when the bytes queued pass the connection's rate
  (`IsNetReady`): each tick the queue first drains by the rate, down to two
  ticks' worth below 0 (each rounded toward 0), then takes the tick's packet,
  its bytes and its `PacketOverhead` (32 for UDP,
  [IpDrv](ipdrv-dll.md#the-net-driver)); there is room while it and the packet
  being built come to 0 or less. So the tick after a packet has room only if
  that packet came to two ticks' worth or less, and the faster the frames, the
  less room an unreliable call finds ([remote functions](#replication)).
- **Frames:** a client runs at most its connection's speed / 64 frames a second
  (40 at 2,600); a dedicated server (the game started with `-SERVER`, no client:
  [the command line](cli-flags.md)) at `NetServerMaxTickRate`
  (`LanServerMaxTickRate` with `-lanplay`), 10 to 120
  (`UGameEngine::GetMaxTickRate`, `0x1038fc60`); a listen server as fast as its
  client draws. A dedicated server has no window, player or console of its own,
  and its map listens without `?listen`.

## Numbering

Both sides number objects and names by the `USES` list (`UPackageMap::Compute`,
`0x1012c710`): the packages in the server's order, each one's objects (its
exports) and names numbered on from the last's. Where one side has an older
generation of a package, both count only what that generation had (each
generation's export and name counts are in the file's header). A name in several
packages takes its first package's number. An older package file (below version
68, as `CoreTexDetail.utx`) has no GUID in its header: its GUID is the last of
its heritage list, its one generation its counts.

- **An object:** a bit; 1 and a channel number for a dynamic actor (its actor
  channel on this connection; 0 for None or an actor without one), 0 and the
  object's number otherwise (`UPackageMapLevel::SerializeObject`, `0x104089f0`);
  an object by number is loaded if it is not (`IndexToObject` with Load). One
  the map has not goes as channel 511 and counts as sent, so goes once.
- **A name:** its number, up to the count of names; the count is None. One the
  map has not goes as -1 (Core.dll `0x1012bf30`), which the other side reads as
  another name.
- **A class's fields:** numbered on from its parent class's: its own replicated
  properties and its net functions that override none, in the order of its
  package's exports (`0x1012c160`).

**A value** (each property type's `NetSerializeItem`):

| Type | Sent as |
|---|---|
| bool | one bit |
| byte | its enum's bits (as many as its names need), or 8 |
| int, float | 4 bytes |
| object, class | as above, dropped unless of the property's class |
| name | as above |
| string | its length (with the terminator, as a compact index) and characters |
| vector | each coordinate rounded, in as many bits as the largest needs (given first, 4 bits), offset to be positive |
| rotator | each component's top byte, after a bit for whether it is not zero |
| plane | four 16-bit numbers, X, Y, Z, W, each rounded |
| any other struct | member by member, its own members first, then those of the struct it extends, each one the package map numbers (`UStructProperty::NetSerializeItem`, Core.dll `0x101691e0`); a static array member's element i at its offset plus i times its count, past the member (`0x10169549`-`0x10169566`), which no replicated stock struct has |

## Replication

Each tick, for each connection with a player and room to send, the server picks
what to send (`ULevel::ServerTickClient`, `0x103a3500`):

- **The viewer:** where the player's view is (`PlayerCalcView`); every other
  tick, where it will be in 0.9 s (0.4 s every fourth tick) at its and its
  base's velocity, up to a wall: the model's line check passing nodes that
  do not block sight (`NF_NotVisBlocking`, `0x103a37d8`, the call at
  `0x103a3880`).
- **The candidates:** each actor with a remote role, once a tick (every dynamic
  actor, and a static one if `bAlwaysRelevant`), when its `NetUpdateFrequency`
  says an update is due: the whole number of updates since the connection's last
  replication changed, each actor's clock 0.023 s on from the one before it. An
  actor a client was sent to keep (`bNetTemporary`) is never one again for that
  client.
- **Priority** (`0x103a4350`): the actor's `GetNetPriority` (its `NetPriority`
  times the time since its last complete update; `SpawnPrioritySeconds` for one
  without a channel, so an unsent actor does not rise) times 3 plus the cosine
  between the player's view direction and the actor's direction from the viewer,
  in 65,536ths; `bNetOptional` ones 100,000 lower. A walking player's pawn
  (`APawn::GetNetPriority`, `0x103c5ff0`) takes, for the time, twice the
  distance between where it will be in half the lag and where the client's copy
  would be by then, over its `GroundSpeed`, plus half the time. The candidates
  go highest first.
- **Relevant or not** (`0x103a3120`), from the most important down, while the
  connection takes more:
  - always if `bAlwaysRelevant`;
  - if owned (up its `Owner`s) by the player or its view target, or one of them;
  - if it has an `AmbientSound` and the viewer is within about half its sound's
    reach (√0.3 of it);
  - if a pawn inside the viewer's `RelevantRadius`;
  - a pawn's weapon as its pawn;
  - not if hidden (`bHidden` or `bOnlyOwnerSee`) and neither blocking players
    nor sounding;
  - otherwise if seen: a line through the BSP from the viewer to it, or to a
    pawn's eyes. A dedicated server's BSP holds no mover, so a closed door
    hides nothing from it ([traces](engine-dll.md#traces)).
- **Deus Ex's `AdditionalViews`:** a player's other viewpoints count as viewers
  too, but the loop tries the first of the three, three times.
- **Channels:** a relevant actor whose class the client knows gets an actor
  channel, and is replicated when the channel has room; one irrelevant for
  `RelevantTimeout` loses it, and the client destroys its copy. A destroyed
  actor's channels close (`UNetDriver::NotifyActorDestroyed`, `0x10409d70`).

`UActorChannel::ReplicateActor` (`0x103fead0`) then writes what changed, against
a copy of what this client last got (`SetChannelActor`, `0x103fd620`): the
class's defaults to begin with, less its config values (cleared so that they
always go, the client's own config being its own). An actor sent to keep has no
copy and is compared with its defaults.

- **The first bunch** (`bNetInitial`): a static or no-delete actor by reference
  (the client has it from the map), any other by class and location, for the
  client to spawn. It is reliable, except for an actor sent to keep, whose one
  unreliable bunch opens and closes the channel; the actor is then one of the
  connection's sent temporaries. A temporary channel goes only once its open
  is acknowledged (`UChannel::ReceivedAcks`, `0x103fac10`); one whose open
  packet is lost stays, its open never acknowledged, for the connection's
  life: the NAK (`UNetConnection::ReceivedNak`, `0x10402f10`) resends the
  reliable bunches and, for an actor channel, marks the lost properties for
  sending again (`UActorChannel::ReceivedNak`, `0x103fd4e0`), and deletes
  nothing.
- **Roles:** `bNetOwner` is whether the connection's player owns the actor (its
  top owner that player's pawn). An autonomous proxy goes as a simulated one
  unless the client owns it or it has no instigator (or its instigator was last
  sent as owned). `Role` and `RemoteRole` each go under the other's field
  number, the roles as the client has them. `bSimulatedPawn` is a pawn sent as a
  simulated proxy.
- **Properties:** those the native list gives (`GetOptimizedRepList`, for
  `Actor`, `Pawn`, `PlayerPawn`, `Mover`, `ZoneInfo`, the two replication infos
  and `Inventory`), and each replicated script property whose value is not
  `Identical` to what the client last got, a string's without case and a
  float's by the x87's compare, so a NaN never goes
  ([`Identical`](core-dll.md#packages-and-linkers)), and whose replication
  statement holds (the statement
  its `RepOwner` names, each evaluated once a call). The classes with a native
  list declare `nativereplication`, and the class net cache leaves their own
  properties out of the script replication (`UPackageMap::GetClassNetCache`,
  Core `0x1012c160`), so their statements are never evaluated: the
  [native lists](#the-native-lists) decide. A reference to a dynamic actor the
  client has no channel for yet compares as None, so it goes once there is one;
  one that went before the client could resolve it is cleared from the copy, so
  it goes again. An always-relevant inventory item sends its script classes'
  values in its first bunch only (`AInventory::ShouldDoScriptReplication`,
  `0x10367e00`).
- **Losses:** each element's last packet and whether it was reliable are kept; a
  lost unreliable one is sent again with the next, and once the client
  acknowledges the channel's open, so is all that went unreliably before it.
- **A full bunch** keeps the rest for the next tick; the time since the last
  update runs on until one goes complete.

**Receiving** (`UActorChannel::ReceivedBunch`, `0x103fd980`): a new channel's
first bunch names the actor, or its class and place; that actor is spawned there
without looking for room, its roles exchanged (a remote-owned spawn). A first
bunch that is not an open ends the game (`GError`, "New actor channel received
non-open packet"), and a spawn that gives no actor fails an assertion
(`InActor`). Each bunch
then sets `bNetOwner` (whether the actor's top owner is a player pawn one of
this machine's viewports plays), and reads fields by number to its end:

- a property (with an element byte in a static array), taken unless the last
  value taken for it came in a later packet, when it is read and dropped;
- a function, run at once with its parameters (a bool is its bit, any other a
  bit for whether it was sent, then its value).

A run of properties comes between the actor's `PreNetReceive` and
`PostNetReceive`, and a spawned actor gets `PostNetBeginPlay` after its first.

- **`PostNetReceive`** (`0x103680d0`): the new place, turn, base and collision
  go in through the calls that keep the level right: the old values back, then a
  far move without the fit check, a move by nothing with the new turn,
  `SetCollisionSize`, `SetCollision`, and for a base each actor's `Bump` with
  the other, then `SetBase`.
  - A moving simulated pawn eases to where the server has it: 100 units off or
    more, straight there; 40 to 100, a smooth move of 35% of the way, and a jump
    halfway if that left more than three quarters of the distance squared; under
    40, a jump 15% of the way.
  - `SimAnim` gives the animation: frame and last frame by 10,000, rate by
    5,000, tween by 1,000 -- the number sent times the double 0.0001,
    0.0002 or 0.001, the product as the x87 holds it rounded once to a float
    (`0x103683cc`-`0x1036840b`) --, a negative last frame for a loop (a
    pawn's `AnimMinRate` then at least 0.5).
  - A mover's `SimInterpolate` gives its interpolation: alpha and rate by
    100, each the number times the double 0.01 so (`0x10368277`-`0x103682ae`),
    the key and the previous one, and `PHYS_MovingBrush`.
  - `bJustTeleported` clears. The local player's `PlayerReplicationInfo.Ping`
    loses half the client's average frame time.
- **Closing** an actor channel on a client destroys its actor
  (`UActorChannel::Destroy`, `0x103fd120`), unless it was sent to keep
  (`bNetTemporary`).

**A client replicates too** (`ULevel::TickNetClient`, `0x103a2f10`): each tick,
while its connection to the server is open, each open actor channel whose actor
is a player pawn with a player -- the local player's own -- goes through the same
`ReplicateActor`. Its own pawn is owned there (`bNetOwner`: its top owner's
player a viewport), and the statements are evaluated as the client has the
roles, so what goes is what a statement sends from a client: the native lists
send nothing but `APlayerPawn`'s (`0x103649d0`): from a client its `Password`
when it differs in more than case (`0x103616e0`), `bReadyToPlay` and each of
`AdditionalViews[0..2]`, None for one that cannot go (`0x10364a24`,
`0x10364f9e`-`0x10365105`; `ViewsServer`); `AActor`'s returns at once
(`0x103618c0`), `APawn`'s client branch (`0x103645a0`) waits on `bNetInitial`,
never a client's, or a demo; the script classes' own statements their values -- Deus Ex's `FrobTarget`,
replicated `if (Role < ROLE_Authority)`, which the server's `ParseRightClick`
picks up. A closed connection there has the client browse `?failed`. Each side
keeps a copy of what the other last got (`SetChannelActor`, `0x103fd620`, on
either side), a value received and taken written into it too (`0x103fdd90`,
`0x103fdfe6`), one dropped as unwanted not.

**On a server** a client's bunch is taken with the roles as the client has them:
a property value or a call only when its replication statement then holds and
the client owns the actor. Anything else is read and dropped ("unwanted").

**Animation** goes packed into `SimAnim` (the `PostNetReceive` scale above), set
where the animation starts rather than when replicated:

- `PlayAnim` (`0x103e0160`) sets all four, an unchanged one's last frame nudged
  up by 1 so that it still goes;
- `LoopAnim` (`0x103e05e0`) all four with the last frame negative, or, on the
  loop already playing, the rate and last frame, nudged alike;
- `TweenAnim` (`0x103e0bd0`) the frame and tween, with no rate or last frame;
- a one-shot animation that ends on an actor with a lower remote role than
  simulated (and not a weapon) sets the frame and rate where it stopped.

**Remote functions** (`AActor::ProcessRemoteFunction`, `0x103e5d90`): every call
of an actor's script function in a net game, and of a native without its own
number, passes this first.

- A simulated or dumb proxy runs only functions marked simulated.
- A function marked for the net goes to the other side instead of running when
  its condition holds: the first declaration's, from its class's replication
  block, evaluated for the actor. From the server it goes to the client whose
  player owns the actor (its top owner a player pawn whose `Player` is a net
  connection), a channel opened for the actor and the actor sent first if that
  client has none; from a client, to the server, and only on an actor the server
  gave it a channel for.
- It goes as its field number and its parameters (a bool its bit, any other a
  bit for whether it is not zero, then its value), reliable as the function is
  marked; an unreliable one is dropped when the connection has no room.

**Ticking by role** (`AActor::Tick`, `0x103a1aa0`), by the roles alone, whatever
the net mode -- no test of the net mode or of the kind of a player's `Player`:

- a pawn whose own `Role` is `ROLE_SimulatedProxy` (`0x103a1fd2`), on a client
  another player's pawn, moves smoothly along its velocity (a player's, off the
  ground by a trace 8 units down and not flying or in water, gaining half the
  zone's gravity) and runs its `Tick`: no state code, timers or physics;
- else an actor whose remote role is autonomous (`0x103a23ce`), on a server a
  client's pawn, runs its state code and timers, and, as any pawn with
  authority, its sight and its pain and speech timers
  ([the senses](engine-dll.md#the-senses)): no `Tick`, life span or physics, it
  moves by the client's `ServerMove`s. A player pawn of them viewing a pawn
  first takes that pawn's view rotation, eye height and, when it holds a weapon,
  the weapon's `PlayerViewOffset` into its `TargetViewRotation`,
  `TargetEyeHeight` and `TargetWeaponViewOffset` (`0x103a23e6`-`0x103a249c`),
  which go to its client, whose `PlayerCalcView` puts them on its copy of the
  pawn viewed. With any role but the authority such an actor runs none of it
  (`0x103a23de`);
- else a dumb proxy, or an actor of no role, only falls (`0x103a2524`);
- anything else ticks as a standalone game's: a player pawn with a `Player` its
  input, `PlayerInput` and `PlayerTick`, any other its `Tick`; its state code,
  timers, life span and physics -- but an autonomous proxy, on a client the
  local player's pawn, has its physics only in its moves (`AutonomousPhysics`,
  `0x103a2763`), a proxy's state code runs, and its latent action counts
  down, in a simulated state alone (`AActor::ProcessState`, `0x103e5b9c`),
  and a proxy whose life span runs out is not destroyed
  ([destroyed actors](engine-dll.md#destroyed-actors)): it stays, its
  `Expired` again each tick, its physics stopped, until its channel closes.

A viewport's own player is spawned with the remote role simulated
(`UGameEngine::Init`, `LoadMap`, `0x1038bf92`), a client's with autonomous (the
`JOIN`'s, `0x103a00c7`); no stock class or map gives an actor that remote role.

### The native lists

Each is its class's replication statements written in C++: a value goes when it
differs from what the client last got and the condition holds, all only on the
server (`Role` the authority). A float differs by its bits, the replication
infos' `Score` and `Deaths` compared as DWORDs, so a change from 0.0 to -0.0
goes and an unchanged NaN does not. A string differs by `appStricmp`
(`0x103616e0`), so one changed in case alone does not go: the replication
infos' names, the
game's name and class, the server's names, the admin's, the messages of the
day and the end's comments. `Mover` (`0x10365320`), `ZoneInfo` (`0x103657a0`)
and `GameReplicationInfo` (`0x10366960`) are their statements exactly. The
others differ:

- **`Actor`** (`0x103618c0`): `SimAnim`, `AnimMinRate` and `bAnimNotify` go with
  `AnimSequence` (a mesh, and a remote role up to simulated proxy unless owned
  with `bClientAnim`, or a demo recording), UE1's statement; Deus Ex's script
  gives `SimAnim` and `AnimMinRate` below simulated proxy and `bAnimNotify` at
  it. The blended animations its script added (`BlendAnimSequence`,
  `SimBlendAnim`, `BlendAnimMinRate`) are in no list and never go. `Physics`,
  `Acceleration` and `bBounce` go to a simulated proxy in its first bunch
  alone, and never to a simulated pawn; to any other remote role while
  `bSimFall` is set (`0x10362f04`, `0x1036328a`), where the statement sends
  them whenever they change (DXEngine's harness's `SimFallServer`).
- **`Pawn`** (`0x10363bc0`): `PlayerRestartState` is in no list and never goes,
  though its statement names it for the owner.
- **`PlayerPawn`** (`0x103649d0`): the owner's list also names
  `bNeverAutoSwitch`, which no statement names, so it has no replication index:
  it pushes index 0, `Actor`'s `bHidden`, the first replicated property of
  Engine.u, and never writes the copy's `bNeverAutoSwitch` (`0x10364cb6`), so
  on a server whose `User.ini` sets `[Engine.PlayerPawn] bNeverAutoSwitch=True`
  each player's `bHidden` goes again every update.
- **`PlayerReplicationInfo`** (`0x10365ca0`): `Actor`'s list only in the first
  bunch (`bNetInitial`).
- **`Inventory`** (`0x10367450`): an always-relevant item past its first bunch
  sends `bHidden` alone; and one not owned by the client, a simulated proxy with
  an `AmbientSound`, sends its `Location` too.

## Demos

A demo is what a level sends a client, kept in a file and played back as a client's level
(`UDemoRecDriver`, `UDemoRecConnection`, `UDemoPlayPendingLevel`). `[Engine.Engine]`
`DemoRecordingDevice` names the driver's class, `Engine.DemoRecDriver`, whose section holds its
settings: `NetServerMaxTickRate` 60, `KeepAliveTime` 1 s, `DemoSpectatorClass`
`UnrealShare.UnrealSpectator`, a class Deus Ex has not. A key the section lacks is
`UNetDriver`'s own, 0 but `MaxClientRate`'s 25,000 (`UNetDriver::StaticConstructor`,
`0x10409080`).

- **The file**: a record for each packet: the frame the driver has counted (4 bytes), its time
  (an 8-byte double), the packet's size (4 bytes) and its bytes
  (`UDemoRecConnection::LowLevelSend`, `0x10406a70`). The driver's time and frame start at 0
  (`InitBase`, `0x10407420`); each of its ticks adds the frame's time, not dilated, and a frame
  (`TickDispatch`, `0x10407f60`).
- **The words** (`ULevel::Exec`, `0x1039dfe0`; `UDemoRecDriver::Exec`, `0x104083c0`):
  `DEMOREC <name>` records into the name, `.dem` added where it does not end so, "Attempting
  to record demo %s" logged; "Demo recording started to %s", or "Demo recording failed:
  Couldn't open demo file %s for writing" and the driver deleted. `DEMOPLAY <url>` reads its
  text as a URL on no base, `.dem` added to its map -- so `DEMOPLAY x.dem`, whose dot is no
  map's or save's extension, names a host and the default map, which gets the `.dem`: a demo
  is named without it --, logs "Attempting to play demo %s", gives up a join under way and
  makes a pending level of the demo's; "Demo playback failed: Couldn't open demo file %s for
  reading" when the file is not there. Either word bare: "You must specify a filename". While
  a demo runs its driver takes `DEMOREC` and `DEMOPLAY` first, "Demo recording currently
  active: %s" or "Demo playback currently active: %s", and `STOPDEMO`, "Demo %s stopped (%d
  frames)": a recording's driver deleted, its connection's control channel closed and sent
  (the file's last packet), then "Closing down demo driver." and the file closed
  (`UNetDriver::Destroy`, `0x10409840`; `UNetConnection::Destroy`, `0x104019e0`;
  `LowLevelDestroy`, `0x10407e50`); a playback's connection closed. A map's load deletes the
  old level's demo driver too (`UGameEngine::LoadMap`, `0x1038c1f0`).
- **Recording** (`UDemoRecDriver::InitListen`, `0x10407870`): one connection
  (`UDemoRecConnection`, `0x104068a0`), open, at 1,000,000 bytes a second and 512-byte
  packets, always ready (`IsNetReady`, `0x10406c80`), and acknowledging itself: it writes no
  acks (`SendAck`, `0x10404360`), and each tick marks all it sent acknowledged, its channels'
  opens too, never times out and never alerts its player for lag or loss
  (`UNetConnection::Tick`, `0x10404a40`). In single player and on a server an
  `Engine.DemoRecSpectator` is spawned at the level's origin, rotation 0, no one's player
  (`SpawnDemoRecSpectator`, `0x10408690`; one that cannot be spawned ends the game, a cast of
  None), and the demo's packages are built as a server's (`BuildServerMasterMap`,
  `0x10388b10`, the game engine's virtual at +0xC0, logging each `Server Package` again); on a
  client they are its server connection's. Then the control channel, and the welcome a server
  gives a client (`ULevel::WelcomePlayer`, `0x1039f500`), sent at frame 0: the `USES` lines,
  `WELCOME LEVEL= LONE=` with `CLIENTDEMO` (single player, a client) or `SERVERDEMO` (a
  server) after it, then the demo driver's `DYNAMICRATE` and `STATICRATE`.
- **Each tick** of the level (`ULevel::Tick`, `0x103a51a0`): the demo driver's dispatch at its
  start, after the net driver's, by the frame's own time; at its end, after the net driver's
  flush, `TickDemoRecord` (`0x103a4b90`), then the demo's flush. A recording runs no more
  frames a second than its driver's `NetServerMaxTickRate`, held to 10..120 -- 60 --, with
  `-lanplay` the level's net driver's `LanServerMaxTickRate`, read whether the level has a net
  driver or not (`UGameEngine::GetMaxTickRate`, `0x1038fd9c`-`0x1038fdb9`): a single player's
  has none.
- **What it records** (`TickDemoRecord`): every actor each tick, none passed over for
  relevance, priority or `NetUpdateFrequency`: one with a remote role, or on a client one of
  the server's (its role neither none nor the authority); in the list's dynamic part, or a
  zone, the `LevelInfo` among them; one sent once to keep, once; not one that is not static
  whose class is (`0x103a4cd4`-`0x103a4d09`); with a channel, its class one the demo's
  packages number. Each goes through `ReplicateActor` with `bDemoRecording` set, and on a
  client `bClientDemoRecording` and its roles exchanged, so it goes as its server sent it.
  Every actor is the demo's own (`bNetOwner`) -- on a client only those of its viewport's
  player (`UActorChannel::ReplicateActor`, `0x103fecf1`-`0x103fed74`) --, so each one's
  replicated `bNetOwner` goes 1; an autonomous proxy goes as a simulated one
  (`0x103feeb1`-`0x103feec9`).
- **Calls** (`AActor::ProcessRemoteFunction`, `0x103e5d90`; `ProcessDemoRecFunction`,
  `0x103e6400`): while a level records, a call of a function for the net, not static, on an
  actor not sent once to keep (on a client not one of its own authority), whose first
  declaration's statement holds with `bDemoRecording` set (on a client `bClientDemoRecording`
  too, the roles exchanged), goes into the demo as a server sends a call, the actor's channel
  opened and the actor sent first where the demo has none; then the call goes on as ever, in
  single player run there. Its parameters are evaluated for the demo and again for the call
  itself. `bClientDemoNetFunc` is set on an actor before a call that came from the other side
  runs (`UActorChannel::ReceivedBunch`, `0x103fe4be`) and cleared after a demo's test of a
  call. `PlaySound` gives the actor's `DemoPlaySound` event the sound first while its level
  records, but on a client (`0x103e2164`-`0x103e22c4`), `PlayOwnedSound` on a client too, with
  its own radius (`0x103e2acd`-`0x103e2b10`); `DemoPlaySound`'s statement is `bDemoRecording`
  alone, and its native plays the sound to the viewports' players (`0x103e1d00`). A recorded
  player takes his view's pitch and yaw into `DemoViewPitch` and `DemoViewYaw` after his
  `PlayerTick` (`AActor::Tick`, `0x103a2616`-`0x103a263b`), which go `if (bDemoRecording)`.
  A destroyed actor's channel closes in the recording too (`ULevel::DestroyActor`,
  `0x10395ba0`).
- **Playback** (`UDemoPlayPendingLevel`, `0x104058f0`; `InitConnect`, `0x10407550`): the
  server's connection, pending, at the same speed and acknowledging itself; the URL's
  `?3rdperson`, `?timebased` and `?noframecap`. Each tick reads the packets whose frame has
  come (with `timebased`, whose time has), one a tick while the connection waits for its
  player; by frame, a packet ahead of the driver's time first waits out the difference, the
  CPU spinning, each packet's wait from the end of the last, so a frame of several packets
  plays slower than it was made (`0x10408052`-`0x1040811c`); the file's end, or a packet not
  read whole ("Failed to read demo file packet"), closes the connection. A packet is read into
  a 520-byte buffer whatever its size. Nothing is sent (`UDemoRecConnection::FlushNet`,
  `0x10406ca0`). The pending level takes every channel, and of the text `USES` and `WELCOME`
  alone (`0x10406080`, "DemoPlayPendingLevel received: %s"): each package found by its name
  or its GUID, or "Don't have package for demo: %s" and the playback waits for good;
  `SERVERDEMO` makes it a third person's; the driver's time set to 0. Its map is the first
  package the demo uses, loaded as a client's (`LoadMap`, `0x1038c607`-`0x1038c6ab`), the
  level's URL the demo's; the Connecting action and a frame drawn, and no `JOIN` (`SendJoin`,
  `0x10405da0`). While it waits the connecting message is the demo's file alone
  (`0x10388976`-`0x103889c5`). Calls for the net go nowhere: a simulated proxy's held off as
  ever, the rest run there (`ProcessRemoteFunction`). A received player pawn takes
  `DemoViewPitch` and `DemoViewYaw` into his view (`PostNetReceive`,
  `0x10368336`-`0x10368370`).
- **The player** (`UDemoRecConnection::HandleClientPlayer`, `0x10406cc0`): the first player
  pawn whose `bNetOwner` comes set while the connection is pending -- in a single player's
  demo the recorded player, ahead of the `DemoRecSpectator` in the level's list -- is the
  viewport's, as a joining client's (`UNetConnection::HandleClientPlayer`, `0x10405290`); with
  `3rdperson`, a spectator of `DemoSpectatorClass` (`Engine.Spectator` for none; one not to be
  had ends the game, the stock ini's), spawned at the level's first `PlayerStart`, flying, an
  admin, owned, of the authority, who takes his view target pawn's view, not from behind, as a
  server's copy of a client's pawn does (`AActor::Tick`, `0x103a2793`-`0x103a2888`). Either way
  the player takes the level's song, faded in, and a console's timedemo turns the frames' cap
  off. The level's Connecting action ends once the player is in, and at the demo's end the
  viewport travels to `?entry` (`ULevel::TickDemoPlayback`, `0x103a4f70`).
- **`Engine.DemoRecSpectator`**, a `MessagingSpectator`: its `ClientMessage`, `TeamMessage`,
  `ClientVoiceMessage` and `ReceiveLocalizedMessage` go into the demo as `RepClientMessage`
  and the rest, `reliable if (bDemoRecording)`; in a playback its simulated `Tick` finds the
  player pawn a viewport plays and the game replication info, gives him it, and passes the
  messages on to him.

## Deus Ex's additions

- **`Actor.RelevantRadius`:** a viewer with one takes every pawn inside it as
  relevant, seen or not.
- **`PlayerPawn.AdditionalViews[3]`:** more viewpoints for relevancy, of which
  only the first works. A viewport window's `SetViewportActor` fills them on
  the pawn its root belongs to
  ([a viewport window](extension-dll.md#a-viewport-window)):
  `APlayerPawn::AddAdditionalView` (`Engine.dll` `0x103ba540`) puts the actor
  in the first empty one, whether it is there already or not, and
  `RemoveAdditionalView` (`0x103ba4c0`) empties the first that holds it and
  moves those after it down a place, the last left as it was. The windows are
  the client's, and a client's pawn sends its `AdditionalViews`
  ([replication](#replication), a client replicates too), which the server's
  `ServerTickClient` (`0x103a3500`) takes for viewers when it picks what is
  relevant: a drone's or a security camera's view gets what is round it.
- **The client's classes checked** (the game's script, `DeusEx.u`): a joined
  player's pawn is called to check its console's class and its root window's
  (`VerifyConsole(Engine.Console)`, `VerifyRootWindow(DeusEx.DeusExRootWindow)`,
  exact classes, no subclass). One that fails tells the server's game, which
  calls back `ForceDisconnect("Invalid Console class, disconnecting")` (or
  `RootWindow`): the line added to the console, then `DisconnectPlayer`. Every
  server with a `DeusExGameInfo` game does it, the modded ones too.
