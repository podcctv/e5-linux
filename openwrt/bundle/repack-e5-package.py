#!/usr/bin/env python3
"""Repack an existing E5 TF installer with the fork-owned E5 overlay.

This is the Windows fallback for the Linux/Docker incremental builder.  It
does not alter the ext4 image or boot image; it replaces the installer hotfix
payload with files from this checkout and records all supplied input hashes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tarfile
import tempfile

TOP = Path(__file__).resolve().parents[2]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def copy_overlay(source, destination):
    copied = []
    for path in sorted(Path(source).rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        relative = path.relative_to(source)
        target = Path(destination) / relative
        if path.is_dir() and not path.is_symlink():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            target.symlink_to(path.readlink(), target_is_directory=path.is_dir())
        else:
            shutil.copy2(path, target)
        copied.append(relative.as_posix())
    return copied


def make_tar(source, destination):
    with tarfile.open(destination, 'w') as archive:
        for path in sorted(Path(source).rglob('*')):
            if path.is_dir() and not path.is_symlink():
                continue
            relative = path.relative_to(source).as_posix()
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            if path.is_file() and path.read_bytes()[:2] == b'#!':
                info.mode = 0o755
            elif path.is_file():
                info.mode = 0o644
            if path.is_file() and not path.is_symlink():
                with path.open('rb') as stream:
                    archive.addfile(info, stream)
            else:
                archive.addfile(info)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-package', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--zip', type=Path, required=True)
    parser.add_argument('--openclash-apk', type=Path, required=True)
    parser.add_argument('--openclash-core', type=Path)
    args = parser.parse_args()

    base = args.base_package.resolve()
    package = args.package.resolve()
    apk = args.openclash_apk.resolve()
    core = args.openclash_core.resolve() if args.openclash_core else None
    if not (base / 'files/e5-hotfix.tar').is_file():
        parser.error('base package is missing files/e5-hotfix.tar')
    if not apk.is_file() or (core and not core.is_file()):
        parser.error('OpenClash input does not exist')
    if package.exists() or args.zip.resolve().exists():
        parser.error('output already exists; choose a new package and zip path')

    shutil.copytree(base, package)
    with tempfile.TemporaryDirectory(prefix='e5-fork-overlay-') as temp:
        hotfix = Path(temp)
        overlay_files = copy_overlay(TOP / 'openwrt/profile-overlays/e5', hotfix)
        apk_target = hotfix / 'etc/e5/packages/luci-app-openclash.apk'
        apk_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(apk, apk_target)
        core_target = None
        if core:
            core_target = hotfix / 'etc/openclash/core/clash_meta'
            core_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(core, core_target)
        manifest = {'apk_sha256': digest(apk_target), 'apk_source': apk.name}
        if core_target:
            manifest.update(core_sha256=digest(core_target), core_source=core.name)
        manifest_path = hotfix / 'etc/e5/openclash-manifest.json'
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        overlay_files.append('etc/e5/openclash-manifest.json')
        make_tar(hotfix, package / 'files/e5-hotfix.tar')

    rev = subprocess.check_output(['git', '-C', str(TOP), 'rev-parse', 'HEAD'], text=True).strip()
    info = {
        'name': package.name,
        'profile': 'e5',
        'source_commit': rev,
        'build_time': datetime.now(timezone.utc).isoformat(),
        'build_type': 'fork overlay repack; existing tested ext4 and boot payload retained',
        'base_package': str(base),
        'base_package_sha256': digest(base / 'files/openwrt.ext4.gz'),
        'hotfix_sha256': digest(package / 'files/e5-hotfix.tar'),
        'profile_overlay_files': sorted(overlay_files),
        'openclash': manifest,
        'hardware_validation': 'not flashed at build time; device validation follows installation',
    }
    (package / 'files/BUILD.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    (package / 'files/VERSION').write_text(
        f'e5-openwrt-flash fork {rev[:12]} (OpenWrt 25.12.5, B28 capability, USB host route fix, OpenClash)\n')

    finalize = runpy.run_path(str(TOP / 'openwrt/bundle/finalize-package.py'))
    finalize['finalize'](package, 'e5', package / 'files/e5-bootctl')
    finalize['write_zip'](package, args.zip.resolve())
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print('package:', package)
    print('zip:', args.zip.resolve())


if __name__ == '__main__':
    main()
