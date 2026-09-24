# IpDrv.dll

The native half of package IpDrv: the sockets. The UDP driver under the
network protocol ([the network](network.md)); the script's TCP and UDP links,
through which the menus and servers reach the master server and each other;
GameSpy's answer to a master server's challenge; and two tools of Epic's as
commandlets, a master server and an update server. How it was read:
[working on the binaries](README.md#working-on-the-binaries).

## The binary

| Property | Value |
|---|---|
| Size | 184,320 bytes |
| Imagebase | `0x10700000` |
| SHA1 | `26ebe7bcfd080e358d4fb1cb03a1efb713f9ca83` |
| Exports | 178; 22 natives |
| Functions | 640 |

It registers seven classes: `InternetLink`, `TcpLink` and `UdpLink`, whose
script layouts match; `TcpNetDriver` and `TcpipConnection`, C++ only (the
SDK's `IpDrvPrivate.h` has them); and `MasterServerCommandlet` and
`UpdateServerCommandlet`, which it does not export. The natives are the
links': eight of `InternetLink`, nine of `TcpLink`, five of `UdpLink`.

## The net driver

- **The socket** (`UTcpNetDriver::InitBase`, `0x1070abb0`): one UDP socket,
  non-blocking, with broadcast and address reuse on, and send and receive
  buffers of 32 KB for a client, 128 KB for a server. A client binds any
  port. A server binds its URL's port (7790 in `DeusEx.ini`), or the next
  free one of the 20 from it -- only that one when the command line gives
  `PORT=`.
- **Receiving** (`TickDispatch`, `0x1070a440`): each tick, every datagram
  waiting, up to 576 bytes each, goes to the connection whose address sent
  it; one from an unknown address, on a server that accepts it
  (`NotifyAcceptingConnection`), opens a new connection.
- **A connection** (`UTcpipConnection`): its packets are at most 512 bytes
  (`MaxPacket`); `LowLevelSend` (`0x10709580`) sends each as one datagram.

## The script's links

What the menus, the server browser and a server's uplink are made of: an
actor per socket, polled each tick.

- **`InternetLink`:** `Resolve` looks a host name up on a thread of its own
  and raises `Resolved` or `ResolveFailed` from the actor's tick
  (`0x10702d70`, `0x107026a0`); `ParseURL`, `GetLocalIP`, `IpAddrToString`,
  `StringToIpAddr`, `GetLastError`, `IsDataPending`, and `Validate` (below).
- **`TcpLink`:** `BindPort`, `Listen`, `Open`, `Close`, `IsConnected`,
  `SendText`, `SendBinary`, `ReadText`, `ReadBinary`. Its tick (`0x10706fb0`)
  goes by its state: listening, it accepts each queued connection into a new
  actor of its `AcceptClass` (`Accepted`); connecting, it waits for the
  connection (`Opened`); connected, it reads what came, and raises
  `ReceivedText`, `ReceivedLine` or `ReceivedBinary` by its link mode when
  its receive mode is by events, and `Closed` at the end; closing, it sends
  what is buffered first.
- **`UdpLink`:** `BindPort`, `SendText` and `SendBinary` to an address,
  `ReadText`, `ReadBinary`. In receive-by-events mode its tick (`0x1070cee0`)
  reads each datagram, up to 4,095 bytes, and raises `ReceivedText`,
  `ReceivedLine` or `ReceivedBinary` with the sender's address.

## The master server

- **The client's side** is script, `DeusEx.u`'s `DeusExGSpyLink`: over TCP to
  `MasterServerAddress`, it waits for `\basic\\secure\` and six characters,
  answers `\gamename\` (the game's name), `\location\`, `\validate\` (the
  challenge put through `Validate`) and `\final\`, and reads back `\ip\`
  entries, an address and port each, until `\final\`. `DeusExServerPing`
  then asks each server for its details over UDP.
- **`Validate(challenge, gameName)`** (`0x107034c0`): GameSpy's answer -- the
  challenge encrypted with the game's key (RC4) and written in eight
  characters of base 64. The key comes from a table of three games
  (`GenerateSecretKey`, `0x107017f0`: Unreal, Unreal Tournament and an old
  version); for any other name it is six spaces, so Deus Ex's answer needs no
  secret.
- **A server's side** is script too, `IpServer.u`'s `UdpServerUplink`
  (heartbeats to the addresses in `DeusEx.ini`) and `UdpServerQuery`
  (answering queries).
- **Epic's master server** is here as a commandlet
  (`UMasterServerCommandlet`, settings in `MasterServer.ini`): it takes
  servers' heartbeats over UDP, checks each with its own challenge, and lists
  them over TCP, or writes them to a file. The GOG build has no `ucc` to run
  it.

## The database

`gamefiles/System/IpDrv.dll.i64` has the class layouts, the UTF-16 strings and
the initializers' names ([working on the binaries](README.md#working-on-the-binaries)),
and by hand the names of the key table and the encryption's helpers
(`GenerateSecretKey`, `rc4_prepare_key`, `rc4`, `trip2kwart`, `encode_ct`).
Each function above carries a one-line comment.
