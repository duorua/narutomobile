<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img alt="LOGO" src="docs/imgs/logo.png" width="256"  />
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blueviolet">
  <img alt="license" src="https://img.shields.io/github/license/duorua/narutomobile">
  <br>
  <img alt="commit" src="https://img.shields.io/github/commit-activity/w/duorua/narutomobile">
  <img alt="stars" src="https://img.shields.io/github/stars/duorua/narutomobile?style=social">
  <img alt="downloads" src="https://img.shields.io/github/downloads/duorua/narutomobile/total?style=social">
  <a href="https://mirrorchyan.com/zh/projects?rid=MaaAutoNaruto&source=MaaAutoNarutogh-badge" target="_blank"><img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5"></a>
</p>

<p align="center">
  简体中文 | <a href="README_EN.md">English</a>
</p>

<div align="center">

# Maa Auto Naruto

An image-recognition-based automation tool for *Naruto Mobile* (火影忍者手游).

</div>

## Quick Start

1. Download the latest version from the [Releases page](https://github.com/duorua/narutomobile/releases/latest)

2. In your emulator settings, set the resolution to **Tablet 16:9** and **lock screen rotation** to landscape for the best results

3. Verify emulator ADB bridging, disable the keep-alive-in-background option, adjust the software settings, then launch

4. The CLI version is no longer bundled with this project. You can download it from [MaaAutoNaruto_cli](https://github.com/duorua/MaaAutoNaruto_cli)

## FAQ

See the [FAQ documentation](docs/guide/faq.md)

## Usage Notes

See the [usage notes documentation](docs/guide/manual.md)

## Features

### Daily

- [x] Launch game

~~-[ ] Auto login~~ (You must log in manually if your session is lost)

- [x] Daily check-in
- [x] Daily Fortune (招财)
- [x] Like leaderboard
- [x] Send stamina
- [x] Daily share
- [x] Organization prayer
- [x] Points Tournament
- [x] Training Path
- [x] Survival Challenge
- [x] Squad Raid
- [x] Free recruitment
- [x] Monthly check-in and ramen
- [x] Guild Mission Hall
- [x] Stamina grinding (Elite Dungeon)
- [x] Stamina grinding (Gear Crafting, beta)
- [x] Stamina grinding (Shura Dungeon)
- [x] Land of Plenty
- [x] Claim activity chests
- [x] Claim mailbox rewards
- [x] Intel Bureau
- [x] Ninja Registration
- [x] Tencent VIP reward claim

### Combat

- [x] Adventure Mode story progression
- [x] Elite Dungeon progression
- [x] Shura Dungeon progression
- [x] Training Path progression
- [x] Weekly wins grind
- [x] Secret Realm (Water, Fire, Body)
- [x] Organization Fortress (cross-server not yet supported)
- [x] Heaven & Earth Battlefield
- [x] More modes [Hundred Ninja]
- [x] More modes [Traceless Battlefield]
- [x] More modes [Orochimaru Trial]
- [x] Rogue Ninja Pursuit (leader not yet supported)

### Shop

- [x] Shop exchange (in testing)
- [x] Black Market Merchant (usually a net loss — beware)

### Utility

- [x] Switch accounts
- [x] Log cleanup
- [x] Close game
- [x] Show touch overlay (debug)
- ~~[x] Completion marker (with auto-mas)~~ AUTO-MAS now supports MFW natively

### Events

- [x] Easy Helper
- [x] Easy Season
- [x] Secret Realm Weekly Chest

#### (The following are mini-game tasks)

- [x] Server-wide ban/pick arena
- [x] Fantasy Trial blessing grind (beta)
- [x] Hot Hands
- [x] Quick Victory
- [x] Summer Rewards
- [x] Gift Bell Ringing
- [x] Jutsu Card Monopoly
- [x] Champion Gift
- [x] Yamanaka Flower Shop
- [x] Red Packet Grab
- [x] Ninja Path Clash
- [x] Bond Pursuit
- [x] Konoha Snack Shop
- [x] New Year Post Office
- [x] Quiz Game
- [x] Gift Crafting / Delicious Cake
- [x] Treasure Trial (reward claim only for now)

### Kage Support

- [x] Land of Plenty
- [x] Guild Mission Hall (in testing)
- [x] Survival Challenge (in testing)
- [x] Squad Raid
- [x] Organization Prayer
- [x] Privilege Shop copper claim

### Secondary Password

- [x] Rogue Ninja Pursuit leader mode (in testing)
- [x] Stamina purchase (in testing)
- [x] Copper Fortune (in testing)
- [x] Squad Raid double rewards (in testing)

## Contributing

Please read the [development documentation](docs/develop/index.md)

## Acknowledgements

This project is powered by **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)**!

The frontend of this project uses **[MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia)** and **[MaaFwApp](https://github.com/Aliothmoon/MaaFwApp)**.

During development, this project referenced and adapted code and documentation from **[M9A](https://github.com/MAA1999/M9A)**.

Update downloads are accelerated via **[Mirror酱 (MirrorChyan)](https://mirrorchyan.com/zh/projects?rid=MaaAutoNaruto)** CDN service.

Thanks to all the contributors of this project:

[![Contributors](https://contrib.rocks/image?repo=duorua/narutomobile)](https://github.com/duorua/narutomobile/graphs/contributors)

### Join us

General chat: 1047724031

Beta testing: 801637524 (we need more screenshot contributors and beta testers!)

Development: 984076079

## Important Notice

The development team commits that this project will not modify the game itself or any related configuration files. This project is open-sourced under the AGPL-3.0 license. Key terms are summarized below:

- **Author:** The MaaAutoNaruto project is authored by MaaAutoNaruto-DevGroup. All rights of MaaAutoNaruto-DevGroup are licensed to [duorua (@duorua)](https://github.com/duorua). Only this authorized person may represent MaaAutoNaruto-DevGroup in exercising all rights.
- **Usage:** Users of MaaAutoNaruto may use this software freely at their own discretion. Under the AGPL-3.0 license, MaaAutoNaruto-DevGroup bears no liability for any losses that may result from its use.
- **Distribution:** MaaAutoNaruto may be freely distributed by anyone, including for commercial profit. When distributing the software directly, the distributor must comply with the AGPL-3.0 license by providing recipients with the project URL, the complete software source code, and the original AGPL-3.0 license text. When distributing a modified version, the distributor must provide the project URL, a complete copy of the pre-modification source code, and the original AGPL-3.0 license text. Violators may face legal consequences. Those engaging in commercial activities with this project must establish their own customer communities and provide their own after-sales support; they may not direct customers to official communities maintained or operated by the MaaAutoNaruto project team. Anyone profiting from open-source community resources will be blacklisted and publicly named.
- **Dissemination:** MaaAutoNaruto in principle allows free dissemination of this software, provided that in all cases the original copyright notice is retained and the existence of MaaAutoNaruto-DevGroup is not concealed. Due to the nature of this software, MaaAutoNaruto-DevGroup respectfully asks that no one mention MaaAutoNaruto or related automation software in official game media (including official accounts and communities) or in game-related content (including fan groups, offline events, and game content discussions). Thank you for your understanding.
- **Derivatives:** MaaAutoNaruto may be further developed or utilized by anyone. Under the AGPL-3.0 license, any derivative works must also be open-sourced under AGPL-3.0 or a compatible license when redistributed.
- **Logos and Artwork:** The `MaaAutoNaruto logo` is not covered by the open-source license. Copyright belongs to [duorua (@duorua)](https://github.com/duorua), and commercial use rights belong to [duorua (@duorua)](https://github.com/duorua). Software users are granted only non-commercial usage rights. You may not use the `MaaAutoNaruto logo` without authorization on the grounds that the open-source license has been granted, nor may you use it for any commercial purpose without permission. The `Do Not Discuss` image used in announcements is subject to the same restrictions. Special thanks to [导演小Z (@daoyanxiaoz)](https://github.com/daoyanxiaoz) for creating the `Do Not Discuss` artwork.

The above terms supplement and emphasize the AGPL-3.0 license as it applies to this project. For anything not mentioned here, the AGPL-3.0 license prevails. In case of conflict, these terms prevail. If anything is unclear, please open an Issue to ask. In the event of a dispute over content not addressed in Issues, MaaAutoNaruto-DevGroup holds final interpretive authority.
