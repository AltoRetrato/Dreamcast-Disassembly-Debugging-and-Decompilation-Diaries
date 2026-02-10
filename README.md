# 🎮 Dreamcast Disassembly, Debugging & Decompilation Diaries

Tools, resources, and notes for reverse-engineering Sega Dreamcast games.

---

## 📑 Table of Contents
- [⚡ TL;DR](#tldr)
- [🛠️ General Tools](#general-tools)
- [📚 Dreamcast Resources](#dreamcast-resources)
- [🐉 Disassembling and Decompiling a Dreamcast game in Ghidra](#ghidra)
    - [🧬 Ghidra Function Identification Databases (FIDB)](#ghidra-fidb)
- [🐞 Flycast as a GDB Server](#flycast-as-a-gdb-server)
- [⌨️ Debugging with a Console GDB Client](#gdb-console-client)
- [🐲 Debugging with Ghidra](#debugging-a-dreamcast-game-with-ghidra)
- [🔍 Reverse Engineering Examples](#reverse-engineering-examples)
- [🧪 Related Projects](#related)
- [🤝 Contributing](#contributing)
- [⚖️ Disclaimer](#disclaimer)

---

## ⚡ TL;DR <a name="#tldr"></a>
- Extract data from disk images with **GD-ROM Explorer**
- Disassemble/decompile Dreamcast binaries with **Ghidra** (+ scripts or FID DBs)
- Debug interactively using **Flycast (GDB server)** + **Ghidra**

[↑ Back to TOC](#-table-of-contents)

---

## 🛠️ General Tools  <a name="#general-tools"></a>
These tools and practices are neither specific to nor required for reverse engineering, but highly recommended.
- **Notes**: Take lots of them. [Obsidian](https://obsidian.md/) is my favorite note-taking app, using Markdown, but even plain text files will do.
- **AI assistant**: [NotebookLM](https://notebooklm.google.com/) is great for finding that section of that document you need.
- **Hex editor**: [ImHex](https://github.com/WerWolv/ImHex).

[↑ Back to TOC](#-table-of-contents)

---

## 📚 Dreamcast Resources <a name="#dreamcast-resources"></a>
- **[dreamcast-docs](https://github.com/Kochise/dreamcast-docs/)** - hardware docs & bare-metal coding.
- **Sega Dreamcast Katana SDKs**: the official SDKs are available on the Internet, somewhere. Search engines and forums should help you find them.
- **[gditools3](https://github.com/AltoRetrato/gditools3)**: A Python program/library to handle Dreamcast GD-ROM image files. (I might update it or rewrite it from scratch someday.)
- **[SiZiOUS - Sega Dreamcast Downloads](https://sizious.com/download/dreamcast/)**: many awesome tools, some with source code.
- **[ROMhacking Utilities](https://www.romhacking.net/?page=utilities&platform=14&perpage=20)**: a few more tools. _PVR Viewer_ and _GD-Rom Explorer_ are essentials!

[↑ Back to TOC](#-table-of-contents)

---

## 🐉 Disassembling and Decompiling a Dreamcast game in Ghidra <a name="#ghidra"></a>

**[Ghidra](https://github.com/NationalSecurityAgency/ghidra)** is a software reverse engineering (SRE) framework, by the NSA.

<details>

<summary>Install Ghidra:</summary>

- Always check the instructions on [GitHub](https://github.com/NationalSecurityAgency/ghidra) (e.g., to install the required JDK version)
- As of this writing, install [JDK 21 64-bit](https://adoptium.net/temurin/releases) 
- Download a Ghidra [release file](https://github.com/NationalSecurityAgency/ghidra/releases) 
- Extract the Ghidra release file (do not extract on top of an existing installation)
- Launch Ghidra: `ghidraRun.bat` (or create a shortcut - you can use the icon in `support\ghidra.ico`)

</details>

If you are not used to Ghidra, I recommend checking the `/docs/CheatSheet.html` file with keyboard shortcuts and more.

Some Ghidra tools I found for Dreamcast RE:
- [ghidra_sdc_ldr](https://github.com/kapdap/ghidra_sdc_ldr) (extension) - Sega Dreamcast loader for GHIDRA. Did work for me on some binaries, didn't work on others. As an extension, it needs to be compiled for your exact Ghidra version. I'm not sure it is worth the trouble, so I think you can skip this one.
- [dc-re-ghidra](https://github.com/iamsh4/dc-re-ghidra) (script) - Ghidra Script/Data for Dreamcast Reverse Engineering. As a Ghidra script, it is much easier to install and use, so I recommend it. Check the repo for installation and usage details.

Get your Dreamcast binaries (e.g., `1ST_READ.BIN`). Use GD-ROM Explorer if you need to extract one from a disk image.

Create a new Ghidra project and import the binaries. Use these settings:
- Format: `Raw Binary` 
- Language: Processor: `SuperH4`, Variant: `default`, Size: `32`, Endian: `little`, Compiler: `default` 
- Options ➔ Base Address: `0x8c010000` (or `0x8c000000` for `IP.BIN`)

Run auto analysis, then run the `dc-re-ghidra` script.

### 🧬 Ghidra Function Identification Databases <a name="#ghidra-fidb"></a>

Ghidra can create and use Function Identification Databases (FID DBs) to automatically name functions in binaries. Basically, they are the equivalent of FLIRT (Fast Library Identification and Recognition Technology) in IDA Pro.

We can create FID DBs from Sega SDKs manually, but Ghidra's `support\analyzeHeadless` and a few Java scripts can help automate the process. The `CreateMultipleLibraries.java` script requires putting the SDK files in a specific folder tree structure, meaning there is still some manual labor involved. The alternatives are to just use the `dc-re-ghidra` function identification feature (which works, but is somewhat limited), or use the Python script below to do most of the work. I tested it (barely) with SDKs R09, R10, and R11, and it probably would need changes to work with other SDK versions. Edit the paths to your SDKs and the tools in the script before running. When processing a single SDK, it took about 1h and 18 GB of disk space on my PC. YMMV.

Download, edit and run [**build_dc_fidb.py**](build_dc_fidb.py)

Add your custom FID DB by opening a binary in Ghidra's CodeBrowser, then going to `Tools` ➔ `Function ID` ➔ `Attach Existing FidDb...`, then selecting a file (e.g., `dc_sdk_r09.fidb`).

You can enable and disable FID DBs via `Tools` ➔ `Function ID` ➔ `Choose active FidDbs`.

To apply your enabled FID DBs, in the `Analysis` menu you can:
- run `Auto Analyze` or `Analyze All Open...`, then ensure `Function ID` is enabled in the `Analyzers` window group.
- select `One Shot` ➔ `Function ID`.


[↑ Back to TOC](#-table-of-contents)

---

## 🐞 Flycast as a GDB Server <a name="#flycast-as-a-gdb-server"></a>

**[Flycast](https://github.com/flyinghead/flycast)** is a multiplatform Sega Dreamcast, Naomi, Naomi 2 and Atomiswave emulator.

You can emulate a Dreamcast with Flycast, either standalone or as a libretro (RetroArch) core. If you don't need to interactively debug a Dreamcast program, just [get a release for your OS of choice](https://github.com/flyinghead/flycast/releases).

But to interactively **debug** a Dreamcast program, you'll need to build Flycast with GDB support. I could not build a stable version with VS 2019, so I used **MSYS2**.

<details>

<summary>Steps for building Flycast with GDB support on Windows via MSYS2 (click to expand)</summary>

- [Install MSYS2](https://www.msys2.org/#installation) in a short ASCII-only path on a NTFS volume, without accents, spaces, symlinks, etc. (e.g., `C:\msys64`)
- Choose a folder (e.g., `md C:\flycast; cd C:\flycast`) and clone the Flycast repo: `git clone https://github.com/flyinghead/flycast.git`
- `cd flycast`
- `git submodule update --init --recursive`
- Open a MSYS2 MINGW64 terminal (`C:\msys64\mingw64.exe`)
- Set up build environment: `pacman -S make mingw-w64-x86_64-ccache mingw-w64-x86_64-cmake mingw-w64-x86_64-lua mingw-w64-x86_64-ninja mingw-w64-x86_64-SDL2 mingw-w64-x86_64-toolchain`
- If you want to update packages (recommended): `pacman -Suy`
- To prune the cache and recover some disk space: `paccache -r`
- `cd /c/flycast/flycast`
- Standalone (recommended)
    - Configure: `cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX=artifact -G Ninja -DUSE_DX9=OFF -DENABLE_GDB_SERVER=ON`
- Core (not tested with GDB)
    - Configure: `cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX=artifact -G Ninja -DUSE_DX9=OFF -DENABLE_GDB_SERVER=ON -DLIBRETRO=ON`
- Build: `cmake --build build --config RelWithDebInfo --target install`

The Flycast executable will be in `C:\flycast\flycast\artifact\bin\flycast.exe` (or `/c/flycast/flycast/artifact/bin/flycast.exe` in the MSYS2 terminal). Run it and enable the GDB server:
- Go to `Settings` ➔ `Advanced` ➔ `Debugging` 
- Check `Enable GDB` and `Wait for connection`
- Click `Done`
- Restart Flycast for those options to take effect

Finally, I recommend putting the Dreamcast BIOS file in the `data` folder (`C:\flycast\flycast\artifact\bin\data`). Many games can run fine without it, but some won't.

Please note that, as of this writing, I believe the GDB server implementation in Flycast is incomplete and/or buggy: some commands don't seem to work (e.g., `u` / `until`), and even though the debugging sessions I started were stable for quite a while, I had to restart them a couple of times.

</details>

[↑ Back to TOC](#-table-of-contents)

---

## ⌨️ Debugging a Dreamcast game with a GDB client from the console <a name="#gdb-console-client"></a>

A Flycast acting as a GDB server needs a GDB client. Ghidra has one, but you can use a simple terminal client as well. The client needs to support SH4, like `gdb-multiarch`. You can install it on MSYS2 with:
- `pacman -S mingw-w64-x86_64-gdb-multiarch`

To test your setup:
- Start Flycast and from it start a program. It should display `Waiting for debugger...`
- Start the GDB client
    - `gdb-multiarch`
        - `set arch sh4`
        - `set endian little`
        - `target remote 127.0.0.1:3263`
 
You should see the message `Remote debugging using 127.0.0.1:3263`. Now you can use GDB commands: try `c` to start the program, `help` if you need some, etc.

[↑ Back to TOC](#-table-of-contents)

---

## 🐲 Debugging a Dreamcast game with Ghidra <a name="#debugging-a-dreamcast-game-with-ghidra"></a>

This is not a Ghidra tutorial, but see the Reverse Engineering Examples section below if you need some help. That being said, to debug a Dreamcast game running on Flycast using Ghidra as a GDB client:
- Launch the game from Flycast (built with GDB support)
- Open your imported SH4 binary (e.g., `1ST_READ.BIN`) in Ghidra's Debugger tool
- Click the bug icon: 🐞🔻 `Configure and Launch 1ST_READ.BIN with..>` ➔ `gdb remote` 
	- `Image`: (don't change)
	- `Target`: remote
	- `Host`: localhost
	- `Port`: 3263
	- `gdb command`: c:\msys64\mingw64\bin\gdb-multiarch.exe
	- `Architecture`: sh4
	- `Endian`: little
	- `Launch` 
- Static Mapping
	- Ghidra treats "Static" programs (your imported .BIN file) and "Dynamic" traces (the live memory inside Flycast) as two separate entities. When you connect to a GDB server, Ghidra creates a new **Trace** to represent the emulator's memory. If Ghidra doesn't know that Trace "A" corresponds to Program "B", it labels the trace as **"noname"** and won't propagate breakpoints from your static analysis to the live target.
	- To fix this and synchronize the windows, you need to create a **Static Mapping**.
	- `Window` ➔ `Debugger` ➔ `Modules` ➔ "Map the current trace to the current program using identical addresses"
	- (or use the `Static Mappings` window)

[↑ Back to TOC](#-table-of-contents)

---

## 🔍 Reverse Engineering Examples <a name="#reverse-engineering-examples"></a>

- Perhaps one or more links might appear in this section...

[↑ Back to TOC](#-table-of-contents)

---

## 🧪 Related Projects <a name="#related"></a>

- [samba-de-amigo-2k_modding](https://github.com/AltoRetrato/samba-de-amigo-2k_modding): Tools and information to help you mod "Samba de Amigo Ver. 2000" for the Dreamcast, with English translations and custom songs.
- [Oneiric Quest](https://github.com/AltoRetrato/Oneiric-Quest): a Dreamcast emulator in VR that lets you play Samba de Amigo with virtual maracas!

[↑ Back to TOC](#-table-of-contents)

---

## 🤝 Contributing <a name="#contributing"></a>
Issues, corrections, PRs, suggestions and links are welcome.

[↑ Back to TOC](#-table-of-contents)

---

## ⚖️ Disclaimer <a name="#disclaimer"></a>

This repository is for **educational and research purposes only**.

- No copyrighted game data, SDKs, BIOS files, or proprietary assets are included.
- Sega, Dreamcast, Katana, and all related trademarks are property of their respective owners.
- Reverse engineering may be restricted by local laws—**you are responsible for complying with them**.
- The author provides this material **as-is**, with no warranty of correctness, fitness, or safety.

Use responsibly.

[↑ Back to TOC](#-table-of-contents)
