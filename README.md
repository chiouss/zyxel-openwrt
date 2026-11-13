# Zyxel OpenWrt 25.12 overlay

Builds OpenWrt 25.12 for Zyxel access points. The layout follows TIP OpenWiFi's
[wlan-ap](https://github.com/Telecominfraproject/wlan-ap): a pinned OpenWrt
release, a patch series on top, an extra package feed, and per-device profiles.

Current added supported models:
- ipq40xx: NWA1123ACv3/WAC500, WAC500H
- ipq50xx: NWA220AX-6E/WAX620D-6E, WAX640S-6E
- ipq807x: NWA110AX/WAX510D, NWA210AX/WAX610D/WAX630S, WAX650S
- filogic: WAX300H

## Layout

- `config.yml`: OpenWrt repository and the release tag the patches apply to
- `patches-25.12/`: `git am` series applied on top of that tag
- `feeds/zyxel/`: packages not available in OpenWrt 25.12
- `profiles/`: one profile per device, plus shared ones (`release`,
  `openwrt-feeds`, `zyxel-feed`) that device profiles include
- `build.py`: clones OpenWrt and applies the patches, regenerates them,
  configures the tree for a profile (`feeds.conf`, feeds, `.config`) and
  builds it

## Building

Install the
[OpenWrt build prerequisites](https://openwrt.org/docs/guide-developer/toolchain/install-buildsystem)
plus `python3-yaml`, then:

```sh
./build.py zyxel_wax300h
```

This clones OpenWrt on the first run (`--clone`) or rebases it afterwards
(`--rebase`), configures the tree for the profile and runs `make download`
and `make`. Arguments after `--` go to the final `make`, for example
`./build.py zyxel_wax300h -- V=s`. The rebase drops commits in `openwrt/`
that were not exported with `./build.py --update` (see below).

or step by step:

```sh
./build.py --clone          # --rebase on later runs
./build.py --setup zyxel_wac500h
make -C openwrt -j$(nproc) download
make -C openwrt -j$(nproc)
```

Images end up in `openwrt/bin/targets/<target>/<subtarget>/`.
`./build.py --list` shows the available profiles, `./build.py --clean`
removes the feeds and `.config` from the tree and `./build.py --help`
lists all actions and options.

## Image configuration

The `release` profile reproduces the configuration of the official OpenWrt
release images, taken from the release's `config.buildinfo` and
`feeds.buildinfo` (for example
<https://downloads.openwrt.org/releases/25.12.6/targets/mediatek/filogic/>):
the same packages (LuCI over HTTPS, package manager, attended sysupgrade),
version settings and all five feeds. The build also selects all kernel
modules, so the kernel gets the same vermagic as the release and the image
installs `kmod-*` and other packages from the official repositories with
`apk`.

Options that only add build outputs (SDK, ImageBuilder, toolchain, SBOM,
all target-specific packages) are disabled to save build time.

Attended sysupgrade and `owut` request images for the device from the
upstream sysupgrade server, which doesn't know these devices, so upgrade
by flashing a sysupgrade image from this overlay instead.

## Changing the patches

`openwrt/` is a normal git checkout with one commit per patch. Edit, amend or
add commits there, then regenerate the series:

```sh
./build.py --update
```

`--rebase` resets `openwrt/` to the pinned tag and re-applies
`patches-25.12/`, dropping any commits that were not exported with
`--update` first.

To move to a newer 25.12 release, change `revision` in `config.yml`, run
`./build.py --rebase`, resolve any conflicts in `openwrt/` and run
`./build.py --update`. Update the feed revisions in
`profiles/openwrt-feeds.yml` to match that release's `feeds.buildinfo`, and
compare `profiles/release.yml` with its `config.buildinfo`, including
`CONFIG_VERSION_REPO`.

## License

`build.py` is derived from wlan-ap's `setup.py` and `gen_config.py` and
stays under its BSD-3-Clause license (see `LICENSE.wlan-ap`). The patches
and packages follow OpenWrt's licensing (GPL-2.0 unless stated otherwise).
