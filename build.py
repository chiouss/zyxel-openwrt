#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
#
# Derived from setup.py and scripts/gen_config.py of TIP OpenWiFi wlan-ap
# (https://github.com/Telecominfraproject/wlan-ap); gen_config.py was
# originally written by John Crispin <john@phrozen.org>.
# Copyright (c) 2024, Telecom Infra Project.

import getopt
import os
import sys
from pathlib import Path
from shutil import rmtree
from subprocess import run

import yaml

base_dir = Path(__file__).resolve().parent
config_file = base_dir / "config.yml"
openwrt = base_dir / "openwrt"
profile_folder = Path(os.getenv("PROFILES", base_dir / "profiles")).absolute()
git_ref = ""
config = None
base = None


def die(msg):
    print(f"### {msg}")
    sys.exit(1)


def usage(code=0):
    print(f"""Usage: {sys.argv[0]} [options] <profile>... [-- <make args>...]
       {sys.argv[0]} [options] <action> [<profile>...]

Without an action, prepare the OpenWrt tree (--clone on the first run,
--rebase afterwards), configure it for the profiles and build.

Tree actions:
      --clone             clone OpenWrt, check out the pinned base, apply
                          the patches
  -r, --rebase            fetch, reset to the pinned base, re-apply the
                          patches
  -u, --update            regenerate the patch folder from the commits in
                          the tree

Configuration actions:
  -s, --setup <profile>...  configure the tree for the profiles: feeds.conf,
                            feeds and .config
  -l, --list              list the available profiles
      --clean             remove the feeds, feeds.conf and .config from
                          the tree
  -h, --help              print this message

Options:
  -c, --config <file>     config file (default: config.yml)
  -d, --directory <dir>   OpenWrt checkout (default: openwrt)
      --reference <repo>  local OpenWrt clone to borrow objects from

Several profiles are merged in the given order. Arguments after "--" are
passed to the final make, for example "-- V=s" or "-- -j1".""")
    sys.exit(code)


# OpenWrt tree and patches


def load_config():
    global config, base
    if not config_file.is_file():
        die(f"Missing {config_file}")
    config = yaml.safe_load(config_file.read_text())
    base = config.get("revision", config["branch"])


def git(*args, check=True):
    return run(["git", "-C", str(openwrt), *args], check=check)


def clone_tree():
    if (openwrt / "Makefile").is_file():
        die("OpenWrt checkout is already present. Please run --rebase")

    print("### Cloning tree")
    cmd = ["git", "clone"]
    if git_ref:
        cmd += ["--reference", git_ref]
    if run(cmd + [config["repo"], str(openwrt)], check=False).returncode:
        die("Cloning the tree failed")


def fetch_tree():
    if not (openwrt / "Makefile").is_file():
        die("OpenWrt checkout is not present. Please run --clone")

    print("### Fetching tree")
    if git("fetch", "--tags", "origin", check=False).returncode:
        die("Fetching the tree failed")


def reset_tree():
    print(f"### Resetting tree to {base}")
    if git("checkout", "-B", config["branch"], base, check=False).returncode:
        die("Resetting tree failed")
    git("reset", "--hard", base)
    link = openwrt / "profiles"
    if link.is_symlink():
        link.unlink()


def patch_list():
    patches = []
    for folder in config.get("patch_folders", []):
        patch_folder = base_dir / folder
        if not patch_folder.is_dir():
            die(f"Patch folder {patch_folder} not found")
        patches.extend(sorted(patch_folder.glob("*.patch"), key=os.path.basename))
    return patches


def apply_patches():
    patches = patch_list()
    print(f"### Applying {len(patches)} patches")

    for patch in patches:
        if git("am", "-3", str(patch), check=False).returncode:
            die(f"Applying {patch.name} failed, resolve it in {openwrt} and regenerate the patches with --update")

    (openwrt / "profiles").symlink_to(profile_folder)
    print("### Patches done")


def update_patches():
    folder = base_dir / config["patch_folders"][0]
    print(f"### Regenerating {folder} from {base}..HEAD")
    for patch in folder.glob("*.patch"):
        patch.unlink()
    git(
        "format-patch",
        "--no-signature",
        "--zero-commit",
        "-N",
        f"{base}..HEAD",
        "-o",
        str(folder),
    )


def prepare_tree():
    if (openwrt / "Makefile").is_file():
        fetch_tree()
    else:
        clone_tree()
    reset_tree()
    apply_patches()


# Profiles and configuration


def load_yaml(fname, profile):
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


def merge_profiles(profiles):
    profile = {"packages": [], "description": [], "diffconfig": "", "feeds": {}}
    for p in profiles:
        profile = load_yaml(p, profile)
    for k in ("profile", "target", "subtarget"):
        if not profile.get(k):
            die(f"No profile sets '{k}'")
    return profile


def clean_tree():
    print("### Cleaning tree")
    rmtree(openwrt / "tmp", ignore_errors=True)
    for d in ("feeds", "package/feeds", "target/linux/feeds"):
        rmtree(openwrt / d, ignore_errors=True)
    for f in ("feeds.conf", ".config"):
        (openwrt / f).unlink(missing_ok=True)


def feed_line(f):
    if "path" in f:
        # A feed "path" is relative to the tree's feeds/ directory, as in wlan-ap.
        path = (openwrt / "feeds" / f["path"]).resolve()
        return f"{f.get('method', 'src-link')} {f['name']} {path}"
    if "revision" in f:
        return f"{f.get('method', 'src-git')} {f['name']} {f['uri']}^{f['revision']}"
    if "tag" in f:
        return f"{f.get('method', 'src-git')} {f['name']} {f['uri']};{f['tag']}"
    return f"{f.get('method', 'src-git')} {f['name']} {f['uri']};{f.get('branch', 'master')}"


def in_tree(*cmd):
    return run(list(cmd), check=False, cwd=openwrt).returncode


def setup_feeds(profile):
    # Upstream scripts/feeds has no "setup" command, write feeds.conf directly.
    lines = [feed_line(f) for f in profile["feeds"].values()]
    (openwrt / "feeds.conf").write_text("\n".join(lines) + "\n")

    if in_tree("./scripts/feeds", "update", "-a"):
        die("Error updating feeds")

    for name in profile["feeds"]:
        if in_tree("./scripts/feeds", "install", "-a", "-f", "-p", name):
            die(f"Error installing feed {name}")


def generate_config(profile):
    t, s, p = profile["target"], profile["subtarget"], profile["profile"]
    cfg = f"CONFIG_TARGET_{t}=y\nCONFIG_TARGET_{t}_{s}=y\n"
    cfg += f"CONFIG_TARGET_{t}_{s}_DEVICE_{p}=y\n"
    cfg += profile["diffconfig"]

    for package in profile["packages"]:
        print(f"Add package to .config: {package}")
        cfg += f"CONFIG_PACKAGE_{package}=y\n"

    (openwrt / ".config").write_text(cfg)
    print("### Configuration written to .config")

    if in_tree("make", "defconfig"):
        die("Error running make defconfig")


def configure(profiles):
    if not (openwrt / "scripts/feeds").is_file():
        die(f"No OpenWrt tree in {openwrt}, run {sys.argv[0]} --clone first")

    profile = merge_profiles(profiles)
    print("### Using the following profiles:")
    for d in profile["description"]:
        print(f" - {d}")

    clean_tree()
    setup_feeds(profile)
    generate_config(profile)


def build(make_args):
    jobs = f"-j{os.cpu_count() or 1}"
    if in_tree("make", jobs, "download"):
        die("make download failed")
    if in_tree("make", jobs, *make_args):
        die("make failed")


def list_profiles():
    print(f"Profiles in {profile_folder}")
    print("\n".join(sorted(p.stem for p in profile_folder.glob("*.yml"))))


def main():
    global config_file, openwrt, git_ref

    args = sys.argv[1:]
    make_args = []
    if "--" in args:
        i = args.index("--")
        args, make_args = args[:i], args[i + 1 :]

    try:
        opts, profiles = getopt.gnu_getopt(
            args,
            "rusc:d:lh",
            [
                "clone",
                "rebase",
                "update",
                "setup",
                "list",
                "clean",
                "config=",
                "directory=",
                "reference=",
                "help",
            ],
        )
    except getopt.GetoptError as err:
        print(err)
        usage(2)

    actions = {
        "--clone": "clone",
        "-r": "rebase",
        "--rebase": "rebase",
        "-u": "update",
        "--update": "update",
        "-s": "setup",
        "--setup": "setup",
        "-l": "list",
        "--list": "list",
        "--clean": "clean",
    }
    action = "build"
    for o, a in opts:
        if o in actions:
            if action != "build":
                die("Only one action can be given")
            action = actions[o]
        elif o in ("-c", "--config"):
            config_file = Path(a).absolute()
        elif o in ("-d", "--directory"):
            openwrt = Path(a).absolute()
        elif o == "--reference":
            git_ref = a
        elif o in ("-h", "--help"):
            usage()

    if make_args and action != "build":
        die("Make arguments are only used when building")
    if action in ("build", "setup") and not profiles:
        usage(1)
    if action not in ("build", "setup") and profiles:
        die(f"--{action} takes no profiles")

    if action in ("build", "clone", "rebase", "update"):
        load_config()

    if action == "clone":
        clone_tree()
        reset_tree()
        apply_patches()
    elif action == "rebase":
        fetch_tree()
        reset_tree()
        apply_patches()
    elif action == "update":
        update_patches()
    elif action == "list":
        list_profiles()
    elif action == "clean":
        clean_tree()
        print("### Tree is now clean")
    else:
        if action == "build":
            prepare_tree()
        configure(profiles)
        if action == "build":
            build(make_args)


if __name__ == "__main__":
    main()
