#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
#
# Derived from setup.py of TIP OpenWiFi wlan-ap
# (https://github.com/Telecominfraproject/wlan-ap),
# Copyright (c) 2024, Telecom Infra Project.

from pathlib import Path
from subprocess import run
import getopt
import os
import sys
import yaml


def die(msg):
	print(f"### {msg}")
	sys.exit(1)


def git(*args, check=True):
	return run(["git", "-C", str(openwrt), *args], check=check)


def clone_tree():
	if (openwrt / "Makefile").is_file():
		die("OpenWrt checkout is already present. Please run --rebase")

	print("### Cloning tree")
	cmd = ["git", "clone"]
	if git_ref:
		cmd += ["--reference", git_ref]
	if run(cmd + [config["repo"], str(openwrt)]).returncode:
		die("Cloning the tree failed")


def fetch_tree():
	if not (openwrt / "Makefile").is_file():
		die("OpenWrt checkout is not present. Please run --setup")

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


def setup_tree():
	patches = patch_list()
	print(f"### Applying {len(patches)} patches")

	for patch in patches:
		if git("am", "-3", str(patch), check=False).returncode:
			die(f"Applying {patch.name} failed, resolve it in {openwrt} "
			    "and regenerate the patches with --update")

	(openwrt / "profiles").symlink_to(base_dir / "profiles")
	print("### Patches done")


def update_patches():
	folder = base_dir / config["patch_folders"][0]
	print(f"### Regenerating {folder} from {base}..HEAD")
	for patch in folder.glob("*.patch"):
		patch.unlink()
	git("format-patch", "--no-signature", "--zero-commit", "-N",
	    f"{base}..HEAD", "-o", str(folder))


def usage(code=0):
	print(f"""Usage: {sys.argv[0]} <action> [options]

Actions:
  -s, --setup             clone OpenWrt, check out the pinned base, apply patches
  -r, --rebase            fetch, reset to the pinned base, re-apply patches
  -u, --update            regenerate the patch folder from the commits in the tree

Options:
  -c, --config <file>     config file (default: config.yml)
  -d, --directory <dir>   OpenWrt checkout (default: openwrt)
      --reference <repo>  local OpenWrt clone to borrow objects from""")
	sys.exit(code)


base_dir = Path(__file__).resolve().parent
config_file = base_dir / "config.yml"
openwrt = base_dir / "openwrt"
git_ref = ""
action = None

try:
	opts, args = getopt.getopt(sys.argv[1:], "sruc:d:h",
		["setup", "rebase", "update", "config=", "directory=", "reference=", "help"])
except getopt.GetoptError as err:
	print(err)
	usage(2)

for o, a in opts:
	if o in ("-s", "--setup"):
		action = "setup"
	elif o in ("-r", "--rebase"):
		action = "rebase"
	elif o in ("-u", "--update"):
		action = "update"
	elif o in ("-c", "--config"):
		config_file = Path(a).absolute()
	elif o in ("-d", "--directory"):
		openwrt = Path(a).absolute()
	elif o == "--reference":
		git_ref = a
	elif o in ("-h", "--help"):
		usage()

if not action:
	usage(1)

if not config_file.is_file():
	die(f"Missing {config_file}")
config = yaml.safe_load(config_file.read_text())
base = config.get("revision", config["branch"])

if action == "setup":
	clone_tree()
	reset_tree()
	setup_tree()
elif action == "rebase":
	fetch_tree()
	reset_tree()
	setup_tree()
elif action == "update":
	update_patches()
