#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
#
# Derived from scripts/gen_config.py of TIP OpenWiFi wlan-ap
# (https://github.com/Telecominfraproject/wlan-ap), originally written by
# John Crispin <john@phrozen.org>. Copyright (c) 2024, Telecom Infra Project.
#
# Run from the top of the OpenWrt tree:
#   ../scripts/gen_config.py <profile> [<profile>...]

from os import getenv
from pathlib import Path
from shutil import rmtree
from subprocess import run
import sys
import yaml

profile_folder = Path(getenv("PROFILES", "./profiles")).absolute()


def die(msg: str):
    print(msg)
    sys.exit(1)


def usage(code: int = 0):
    print(
        f"""Usage: {sys.argv[0]} <profile> [<profile>...]
       {sys.argv[0]} list|clean|help

    clean           Remove feeds and .config
    list            List available profiles
    help            Print this message
    """
    )
    sys.exit(code)


def load_yaml(fname: str, profile: dict):
    profile_file = (profile_folder / fname).with_suffix(".yml")

    if not profile_file.is_file():
        die(f"Profile {fname} not found")

    new = yaml.safe_load(profile_file.read_text())
    for n in new:
        if n in {"profile", "target", "subtarget"}:
            if profile.get(n):
                die(f"Duplicate tag found {n}")
            profile[n] = new[n]
        elif n == "description":
            profile["description"].append(new[n])
        elif n == "packages":
            profile["packages"].extend(new[n])
        elif n == "diffconfig":
            profile["diffconfig"] += new[n]
        elif n == "feeds":
            for f in new[n]:
                if not f.get("name") or not (f.get("uri") or f.get("path")):
                    die(f"Found bad feed {f}")
                profile["feeds"][f["name"]] = f

    for i in new.get("include", []):
        profile = load_yaml(i, profile)
    return profile


def clean_tree():
    print("Cleaning tree")
    rmtree("./tmp", ignore_errors=True)
    for d in ("feeds", "package/feeds", "target/linux/feeds"):
        rmtree(d, ignore_errors=True)
    for f in ("feeds.conf", ".config"):
        Path(f).unlink(missing_ok=True)


def merge_profiles(profiles):
    profile = {"packages": [], "description": [], "diffconfig": "", "feeds": {}}
    for p in profiles:
        profile = load_yaml(p, profile)
    for k in ("profile", "target", "subtarget"):
        if not profile.get(k):
            die(f"No profile sets '{k}'")
    return profile


def feed_line(f: dict):
    if "path" in f:
        path = (Path("feeds") / f["path"]).resolve()
        return f'{f.get("method", "src-link")} {f["name"]} {path}'
    if "revision" in f:
        return f'{f.get("method", "src-git")} {f["name"]} {f["uri"]}^{f["revision"]}'
    if "tag" in f:
        return f'{f.get("method", "src-git")} {f["name"]} {f["uri"]};{f["tag"]}'
    return f'{f.get("method", "src-git")} {f["name"]} {f["uri"]};{f.get("branch", "master")}'


def setup_feeds(profile):
    # Upstream scripts/feeds has no "setup" command, write feeds.conf directly.
    # A feed "path" is relative to the feeds/ directory, as in wlan-ap.
    lines = [feed_line(f) for f in profile["feeds"].values()]
    Path("feeds.conf").write_text("\n".join(lines) + "\n")

    if run(["./scripts/feeds", "update", "-a"]).returncode:
        die("Error updating feeds")

    for name in profile["feeds"]:
        if run(["./scripts/feeds", "install", "-a", "-f", "-p", name]).returncode:
            die(f"Error installing feed {name}")


def generate_config(profile):
    t, s, p = profile["target"], profile["subtarget"], profile["profile"]
    config_output = f"""CONFIG_TARGET_{t}=y
CONFIG_TARGET_{t}_{s}=y
CONFIG_TARGET_{t}_{s}_DEVICE_{p}=y
"""

    config_output += profile["diffconfig"]

    for package in profile["packages"]:
        print(f"Add package to .config: {package}")
        config_output += f"CONFIG_PACKAGE_{package}=y\n"

    Path(".config").write_text(config_output)
    print("Configuration written to .config")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage(1)

    if sys.argv[1] == "help":
        usage()

    if sys.argv[1] == "list":
        print(f"Profiles in {profile_folder}")
        print("\n".join(sorted(p.stem for p in profile_folder.glob("*.yml"))))
        sys.exit(0)

    if sys.argv[1] == "clean":
        clean_tree()
        print("Tree is now clean")
        sys.exit(0)

    if not Path("scripts/feeds").is_file():
        die("Run this from the top of the OpenWrt tree")

    profile = merge_profiles(sys.argv[1:])

    print("Using the following profiles:")
    for d in profile["description"]:
        print(f" - {d}")

    clean_tree()
    setup_feeds(profile)
    generate_config(profile)
    print("Running make defconfig")
    if run(["make", "defconfig"]).returncode:
        die("Error running make defconfig")
