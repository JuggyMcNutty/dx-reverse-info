# IpDrv.dll

The native half of package IpDrv, the sockets:

- the UDP net driver under the network protocol ([the network](network.md));
- the script's TCP and UDP links, through which the menus and servers reach the master
  server and each other;
- GameSpy's answer to a master server's challenge;
- two tools of Epic's as commandlets: a master server and an update server.

Method: [working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 184,320 bytes |
| Imagebase | `0x10700000` |
| SHA1 | `26ebe7bcfd080e358d4fb1cb03a1efb713f9ca83` |
| Exports | 178; 22 natives |
| Functions | 640 |

It registers seven classes:

- `InternetLink`, `TcpLink` and `UdpLink`, whose script layouts match;
- `TcpNetDriver` and `TcpipConnection`, C++ only (the SDK's `IpDrvPrivate.h` has them);
- `MasterServerCommandlet` and `UpdateServerCommandlet`, which it does not export.

The natives are the links': eight of `InternetLink`, nine of `TcpLink`, five of `UdpLink`.

## The net driver

- **The socket** (`UTcpNetDriver::InitBase`, `0x1070abb0`): one UDP socket, non-blocking,
  with broadcast and address reuse on; send and receive buffers of 32 KB for a client,
  128 KB for a server. A client binds any port. A server binds its URL's port (7790 in
  `DeusEx.ini`), or the next free one of the 20 from it; only that one when the command line
  gives `PORT=`.
- **Its address**, which it binds (`getlocalhostaddr`, `0x10703eb0`): every one of the
  machine's (`0.0.0.0`), unless the command line names one (`MULTIHOME=a.b.c.d`) or gives
  `-PRIMARYNET`, which takes the first address of the machine's own name. A server's
  `InitListen` (`0x1070a1d0`) writes it, as `a.b.c.d`, and the port it bound into the
  level's URL ([a server's own URL](network.md#addresses)), and logs
  `TcpNetDriver on port <port>`.
  `LowLevelGetNetworkNumber` (`0x1070a9e0`) answers it as `a.b.c.d`;
  `LowLevelGetRemoteAddress` (`0x10709800`) a connection's other end as `a.b.c.d:port`, the
  port left off when 0 ([the scripts' addresses](network.md#addresses)).
- **Receiving** (`TickDispatch`, `0x1070a440`): each tick, every datagram waiting, up to
  576 bytes each, goes to the connection whose address sent it. One from an unknown address,
  on a server that accepts it (`NotifyAcceptingConnection`), opens a new connection.
- **A connection** (`UTcpipConnection`, `0x107092d0`): packets of at most 512 bytes
  (`MaxPacket`), each counted against the rate as 32 bytes more (`PacketOverhead`,
  [packets](network.md#packets)); `LowLevelSend` (`0x10709580`) sends each as one datagram.

## The script's links

What the menus, the server browser and a server's uplink are made of: an actor per socket,
polled each tick. An `IpAddr` is in host byte order (the address's first number in its top
byte), its port a plain number. A new link is set up by its C++ constructor over the class's
defaults: text link mode, receive by events, no socket (`0x10702480`).

- **`InternetLink`:**
  - `Resolve` looks a host name up on a thread of its own and raises `Resolved` or
    `ResolveFailed` from the actor's tick (`0x10702d70`, `0x107026a0`), the port 0.
  - `IpAddrToString` writes `a.b.c.d:port`; `StringToIpAddr` takes the address alone (with
    a port it fails), the port 0.
  - `ParseURL`, `GetLocalIP` (the first address of the machine's own name), `GetLastError`,
    `IsDataPending`, and `Validate` ([below](#the-master-server)).
- **`TcpLink`:** `BindPort` (any port when given none; with `bUseNextAvailable`, the first
  free of the 20 from the one given), `Listen`, `Open`, `Close`, `IsConnected`, `SendText`
  (a line end added in line mode, everything queued in the send FIFO, the whole length
  answered), `SendBinary`, `ReadText`, `ReadBinary`. Its tick (`0x10706fb0`) goes by its
  state:
  - listening: it accepts a queued connection (`CheckConnectionQueue`) into a new actor of
    its `AcceptClass`, connected and in the listener's link mode, or with none into itself
    (its `RemoteSocket`), and raises `Accepted` on the one that took it;
  - connecting: it waits for the socket to turn writable (`CheckConnectionAttempt`) and
    raises `Opened`. On Windows a failed connection never does; the script's own timer
    gives up;
  - connected, and while a close is pending: it reads (`PollConnections`). By events, one
    read a tick of up to 999 bytes, raised whole as `ReceivedText`, `ReceivedLine` or
    `ReceivedBinary` by the link mode; by hand, it only marks `DataPending`. Then it sends
    what the FIFO holds (`FlushSendBuffer`); a pending close, once all is sent, shuts the
    sending side (`ShutdownConnection`);
  - in any state, a connection that reads as ended (a peek of one byte finding nothing, or
    an error other than would-block) is closed, the link goes back to initialized unless it
    is still listening, and `Closed` is raised.
- **`UdpLink`:** `BindPort` makes the socket (broadcast on, non-blocking) and binds as
  `TcpLink`'s does. `SendText` sends the text as it is, no line end in any mode, and answers
  false only when nothing went. `SendBinary`, `ReadText`, `ReadBinary`. Its tick
  (`0x1070cee0`), by events, reads one datagram a tick, up to 4,095 bytes, and raises it
  whole as `ReceivedText`, `ReceivedLine` or `ReceivedBinary` with the sender's address; by
  hand, it only marks `DataPending`.

## The master server

- **The client's side** is script, `DeusEx.u`'s `DeusExGSpyLink`. Over TCP to
  `MasterServerAddress`, it waits for `\basic\\secure\` and six characters, answers
  `\gamename\` (the game's name), `\location\`, `\validate\` (the challenge put through
  `Validate`) and `\final\`, and reads back `\ip\` entries, an address and port each, until
  `\final\`. `DeusExServerPing` then asks each server for its details over UDP.
- **`Validate(challenge, gameName)`** (`0x107034c0`): GameSpy's answer, the challenge
  encrypted with the game's key (RC4) and written in eight characters of base 64. The key
  comes from a table of three games (`GenerateSecretKey`, `0x107017f0`: Unreal, Unreal
  Tournament and an old version); for any other name it is six spaces, so Deus Ex's answer
  needs no secret.
- **A server's side** is script too, `IpServer.u`'s `UdpServerQuery` (answering queries)
  and `UdpServerUplink`. Once its master server's address resolves, it sends a heartbeat,
  `\heartbeat\<query port>\gamename\deusex`, then another each `UpdateMinutes`, from the
  query port's next; the master then asks the query port. It runs only with its config
  `DoUplink` set: `[IpServer.UdpServerUplink] DoUplink=True`, or on its `ServerActors`
  line, whose settings are in before its `PreBeginPlay`. Without it, it stops as it begins
  (`DoUplink is not set.  Not connecting to Master Server.`), as the GOG build's ini leaves
  it, so a game hosted from the menus is never listed. Its check for a listen server is
  commented out in the script: with `DoUplink` set, a listen server announces itself too,
  dedicated or not.
- **Epic's master server** is here as a commandlet (`UMasterServerCommandlet`, settings in
  `MasterServer.ini`): it takes servers' heartbeats over UDP, checks each with its own
  challenge, and lists them over TCP, or writes them to a file. The GOG build has no `ucc`
  to run it.
