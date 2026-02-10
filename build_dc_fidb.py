#!/usr/bin/python3
# -*- coding: utf-8 -*-
# build_dc_fidb.py
# =================
#
# 2026.02.08  1st version

# This script builds Function ID databases (FIDB) from Dreamcast SDKs.
# Tested with SDK r09, r10, and r11, and Ghidra 12.0 on Windows 11.
# Change the configuration and "__main__" sections as needed.
# Run once with `DEBUG = True` for a dry run.
# For some SDKs, up to 1.5 GB of disk space might be needed.
# Might need changes for different SDK versions.


import os
import stat
import shutil
import tempfile
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DEBUG       = False   # Set to False to actually create folders, copy files, and run Ghidra to create the .fidb file(s)
GHIDRA_HOME = os.environ.get("GHIDRA_HOME") or \
              r"C:\Program Files\ghidra_12.0_PUBLIC_20251205\ghidra_12.0_PUBLIC"

ANALYZE     = Path(GHIDRA_HOME) / "support" / "analyzeHeadless.bat"
if not ANALYZE.exists():
    print(f"Ghidra not installed or GHIDRA_HOME not set correctly.\nNot found: {ANALYZE}")
    exit(1)
ANALYZE = str(ANALYZE)

tools = {
    "ar":       { "rel": True, "path": Path(r"Utl\Dev\Gnu\Bin\ar.exe")       }, # Use "rel: False" if using absolute paths
    "libsplit": { "rel": True, "path": Path(r"Utl\Dev\Hitachi\libsplit.exe") }, # Use "rel: True"  if paths are relative from SDK root
    "elfcnv":   { "rel": True, "path": Path(r"Utl\Dev\Hitachi\elfcnv.exe")   },
}


# ---------------------------------------------------------------------
# Filters and constants
# ---------------------------------------------------------------------

VALID_EXTS   = {".o", ".a", ".elf", ".obj", ".lib"}
IGNORE_DIRS  = {"demo", "sample", "vmutool"}
IGNORE_FILES = {"copying.lib"}


def should_ignore(path: Path) -> bool:
    lower = str(path).lower()

    if path.name.lower() in IGNORE_FILES:
        if DEBUG:
            print(f"[IGNORE] file: {path}")
        return True

    for d in IGNORE_DIRS:
        if f"/{d}/" in lower or f"\\{d}\\" in lower:
            if DEBUG:
                print(f"[IGNORE] dir ({d}): {path}")
            return True

    return False


def is_ar_archive(path: str|Path) -> bool:
    if str(path).lower().endswith((".a", ".elf.lib")):
        return True
    if str(path).lower().endswith(".lib"):
        with open(path, "rb") as f:
            magic = f.read(7)
        return magic == b"!<arch>"
    return False


def is_elf(path: str|Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except IOError:
        return False


# ---------------------------------------------------------------------
# Compiler / runtime classification
# ---------------------------------------------------------------------

def detect_compiler(path: Path) -> str | None:
    parts = [p.lower() for p in path.parts]

    # Some .obj files are actually .elf.obj,
    # so we check for folder names first,
    # then magic signature, 
    # and use extensions as a last resort.

    if any(p in parts for p in ("gnu", "sh-elf")):
        return "gcc"

    if any(p in parts for p in ("codewarrior", "mwerks", "mw")):
        return "shc"

    if path.suffix.lower() in {".a", ".o", ".elf"} or is_ar_archive(path):
        return "gcc"

    if path.suffix.lower() in {".lib", ".obj"}:
        return "shc"

    return None


def detect_variant(path: Path) -> str:
    parts = [p.lower() for p in path.parts]

    for token in (
        "m4-single-only",
        "m4-single",
        "mnomacsave",
        "m4",
        "ml",
    ):
        if token in parts:
            return token

    return "default"


def move_tmp_files(tmpdir: Path, dst_dir: Path) -> int:
    num_moved = 0
    for extracted_file in tmpdir.iterdir():
        # Check if destination file already exists
        dst_file = dst_dir / extracted_file.name
        if dst_file.exists():
            print(f"[WARN] extraction destination already exists: {dst_file}")
            continue
        shutil.move(str(extracted_file), dst_file)
        num_moved += 1
    return num_moved


def extract_or_copy(tool: str, src: Path, dst_dir: Path):
    # tool == "copy" for simple copy.
    # Otherwise extract archive to a temporary location first,
    # then move the extracted files to the destination directory.
    # Return the number of files extracted.

    num_extracted = 0

    if tool in tools and not tools[tool].get("exists", False):
        print(f"[WARN] {tool} not found: {tools[tool]['path']} - cannot process {src.name}")

    elif tool == "copy":
        # If the destination file already exists, warn and skip copy/extract.
        dst_file = dst_dir / src.name
        if dst_file.exists():
            print(f"[WARN] destination already exists: {dst_file} - skipping copy")
        else:
            print(f"[COPY] {src}\t-> {dst_file}")
            shutil.copy2(src, dst_file)

    elif tool in ("ar", "libsplit"):
        print(f"[EXTRACT] Using {tool} to extract {src.name} in {dst_dir}")
        with tempfile.TemporaryDirectory() as tmpdirname:

            # Copy archive to temp folder, extract files, delete archive copy
            tmpdir = Path(tmpdirname)
            try:
                shutil.copy2(src, tmpdir / src.name)
                if tool == "ar":
                    subprocess.run([str(tools["ar"]["path"]), "xo", src.name], cwd=tmpdir)
                elif tool == "libsplit":
                    subprocess.run([str(tools["libsplit"]["path"]), src.name], cwd=tmpdir, capture_output=True)
                os.remove(tmpdir / src.name)
            except Exception as e:
                print(f"[ERROR] {tool} extraction failed for {src.name}: {e}")

            # Process extracted files
            if tool == "libsplit":
                # Convert .obj files to .elf using elfcnv
                for f in tmpdir.iterdir():
                    if f.suffix == ".obj":
                        try:
                            subprocess.run([str(tools["elfcnv"]["path"]), f.name, f.with_suffix(".elf").name], cwd=tmpdir, capture_output=True)
                            os.remove(f.with_suffix(".obj"))
                        except Exception as e:
                            print(f"[ERROR] elfcnv failed for {f.name}: {e}")
            elif tool == "ar":
                for f in tmpdir.iterdir():
                    # Some extracted files have a read-only attribute,
                    # and some ELF files have wrong or no file extension.
                    # Let's fix those issues.
                    if f.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
                        f.chmod(0o644)
                    if f.suffix.lower() != ".elf" \
                       and is_elf(f):
                            f.rename(f.with_suffix(".elf"))
            num_extracted = move_tmp_files(tmpdir, dst_dir)

    else:
        print(f"[WARN] unknown tool: {tool}")

    return num_extracted


def create_extra_files(project_root: Path, sdk_name: str, compiler: str):
    props_path = project_root / "CreateMultipleLibraries.properties"
    with open(props_path, "w") as f:
        f.write(
f"""Duplicate Results File OK = duplicates.txt
Do Duplication Detection Do you want to detect duplicates = true
Choose destination FidDB Please choose the destination FidDB for population = {sdk_name}.fidb
Select root folder containing all libraries (at a depth of 3): = /{compiler}
Common symbols file (optional): OK = common_symbols.txt
Enter LanguageID To Process Language ID: = SuperH4:LE:32:default
"""
)
    # Create empty duplicates.txt and common_symbols.txt
    (project_root / "duplicates.txt").touch()
    (project_root / "common_symbols.txt").touch()

    print(f"[INFO] Created {props_path}, empty duplicates.txt and common_symbols.txt")

# ---------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------

def build_fidb(fidb_name: str, sdk_root: str | Path):
    sdk_root     = Path(sdk_root).resolve()      # source
    project_root = Path(f"fid_work_{fidb_name}") # destination

    # Set / check tool paths
    for tool in tools:
        if tools[tool].get("rel", False):
            tools[tool]["path"] = sdk_root / tools[tool]["path"] # Adjust relative path
        if not tools[tool].get("exists", False):
            tools[tool]["exists"] = tools[tool]["path"].exists() # Check existence

    if DEBUG:
        print(f"[DEBUG] SDK root     : {sdk_root}")
        print(f"[DEBUG] Project root : {project_root}")
        for tool in tools:
            print(f"[DEBUG] {tool:<13}: ({'found' if tools[tool]['exists'] else 'MISSING'}) {tools[tool]['path']}")
        print()
    else:
        if project_root.exists():
            print(f"{project_root} already exists. Remove it before running the script.")
            return
        project_root.mkdir(parents=True, exist_ok=True)
        (project_root / "ghidraproj").mkdir(exist_ok=True)

    copied = 0
    compilers = set()

    for file in sdk_root.rglob("*"):
        # Skip unwanted files
        if not file.is_file() or \
           file.suffix.lower() not in VALID_EXTS or \
           should_ignore(file):
            continue

        compiler = detect_compiler(file)
        if compiler is None:
            print(f"[WARN] unknown compiler: {file}")
            continue
        compilers.add(compiler)

        version = detect_variant(file)
        library = file.name

        dst_dir  = project_root / compiler / library / version / sdk_root.name

        if not DEBUG:
            if not dst_dir.exists():
                print(f"[MKDIR] {dst_dir}")
                dst_dir.mkdir(parents=True, exist_ok=True)

        # Unpack archives or copy files
        tool = "copy"
        if   is_ar_archive(file):           tool = "ar"
        elif file.suffix.lower() == ".lib": tool = "libsplit"
        if DEBUG:
            print(f"[INFO] {tool}: {file}\t-> {dst_dir}")
            copied += 1
        else:
            copied += extract_or_copy(tool, file, dst_dir)

        # if copied > 200: break # Limit used for testing

    if copied == 0:
        print("No SDK files were copied. Check filters or paths.")
        exit(1)

    print(f"[+] Copied {copied} files")

    cmd1 = [
        ANALYZE,
        "ghidraproj", fidb_name,
        # Add "-import" lines for each compiler/platform
        *[item for compiler in compilers for item in ("-import", compiler)],
        "-recursive",
        "-processor",  "SuperH4:LE:32:default",
        "-preScript",  "FunctionIDHeadlessPrescript.java",
        "-postScript", "FunctionIDHeadlessPostscript.java",
        "-scriptlog",  "script.log",
        "-log",        "analyze.log",
    ]

    cmd2 = [
        ANALYZE,
        "ghidraproj", fidb_name,
        "-noanalysis",
        "-propertiesPath", ".",
       #"-scriptPath",     f"{project_root}",
        "-preScript",      "CreateEmptyFidDatabase.java", f"{fidb_name}.fidb",
        "-preScript",      "FunctionIDHeadlessPrescript.java",
        "-preScript",      "CreateMultipleLibraries.java",
        "-log",            "generation.log",
    ]

    if DEBUG:
        print()
        print("AnalyzeHeadless commands:")
        print(" ".join(cmd1))
        print(" ".join(cmd2))
        print()
        print("DEBUG mode is ENABLED.")
        print("No folders were created, no files were copied,")
        print("and analyzeHeadless was NOT invoked.")
        print()
        print("Set DEBUG = False in the script to perform the actual build.")
        return

    # -----------------------------------------------------------------
    # Run analyzeHeadless
    # -----------------------------------------------------------------

    try:
        print("[RUN ] analyzeHeadless (1/2)")
        subprocess.check_call(cmd1, cwd=project_root)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] analyzeHeadless first run failed: {e}")
        raise

    # Create CreateMultipleLibraries.properties, empty duplicates.txt & common_symbols.txt
    create_extra_files(project_root, fidb_name, list(compilers)[0])

    try:
        print("[RUN ] analyzeHeadless (2/2)")
        subprocess.check_call(cmd2, cwd=project_root)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] analyzeHeadless second run failed: {e}")
        raise

    print(f"[+] FIDB generated: {fidb_name}.fidb")


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    os.chdir(r"E:\Games\Dreamcast\Samba2K_hack\sdk"); # Set your SDK root here for testing
    # sdk_root is relative from where you invoke this script, 
    # i.e., run it from the parent folder containing the SDKs in subfolders,
    # or set it to an absolute path.
    #build_fidb(fidb_name="dc_sdk_r09", sdk_root="r09")
    #build_fidb(fidb_name="dc_sdk_r10", sdk_root="r10")
    build_fidb(fidb_name="dc_sdk_r11", sdk_root="r11")