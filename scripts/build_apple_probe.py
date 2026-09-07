"""Build the bounded CP1 probe using installed development profiles, never portal writes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import plistlib
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = "app.keikeu.v08probe"


def build(platform: str) -> Path:
    """Keep profiles, generated entitlements, compiler output and apps ignored."""
    output = ROOT / "tests/test-vault/cp1" / platform
    output.mkdir(parents=True, exist_ok=True)
    expected = "OSX" if platform == "macos" else "iOS"
    profiles = []
    for directory in (
        Path.home() / "Library/Developer/Xcode/UserData/Provisioning Profiles",
        Path.home() / "Library/MobileDevice/Provisioning Profiles",
    ):
        for path in directory.glob("*"):
            decoded = subprocess.run(["security", "cms", "-D", "-i", str(path)], capture_output=True)
            if decoded.returncode:
                continue
            profile = plistlib.loads(decoded.stdout)
            entitlements = profile.get("Entitlements", {})
            identifier = entitlements.get("application-identifier", entitlements.get("com.apple.application-identifier", ""))
            if (identifier.endswith("." + BUNDLE_ID)
                    and expected in profile.get("Platform", [])
                    and profile["ExpirationDate"].replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)):
                profiles.append((path, profile))
    if len(profiles) != 1:
        raise SystemExit(f"Need exactly one current {platform} development probe profile; found {len(profiles)}")
    profile_path, profile = profiles[0]
    identities = subprocess.check_output(["security", "find-identity", "-v", "-p", "codesigning"], text=True)
    certificate = next((hashlib.sha1(cert).hexdigest().upper() for cert in profile["DeveloperCertificates"]
                        if hashlib.sha1(cert).hexdigest().upper() in identities), None)
    if certificate is None:
        raise SystemExit("Profile has no matching local signing identity")
    app = output / "KeikeuProbe.app"
    contents = app / "Contents" if platform == "macos" else app
    executable_dir = contents / "MacOS" if platform == "macos" else app
    executable_dir.mkdir(parents=True, exist_ok=True)
    info = {
        "CFBundleIdentifier": BUNDLE_ID, "CFBundleName": "KeikeuProbe",
        "CFBundleExecutable": "KeikeuProbe", "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1", "CFBundleShortVersionString": "0.8.0",
        "NSUbiquitousContainers": {"iCloud.app.keikeu.v08probe": {
            "NSUbiquitousContainerIsDocumentScopePublic": False,
            "NSUbiquitousContainerName": "keikeu probe",
            "NSUbiquitousContainerSupportedFolderLevels": "Any",
        }},
    }
    if platform == "macos":
        info["LSMinimumSystemVersion"] = "15.7"
    else:
        info.update({"MinimumOSVersion": "18.0", "UIDeviceFamily": [1],
                     "UILaunchScreen": {}, "UISupportedInterfaceOrientations": ["UIInterfaceOrientationPortrait"]})
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    shutil.copyfile(profile_path, contents / ("embedded.provisionprofile" if platform == "macos" else "embedded.mobileprovision"))
    allowed = {"application-identifier", "com.apple.application-identifier", "com.apple.developer.team-identifier",
               "com.apple.developer.icloud-container-identifiers", "com.apple.developer.ubiquity-container-identifiers",
               "com.apple.developer.icloud-services", "get-task-allow"}
    entitlements = {key: value for key, value in profile["Entitlements"].items() if key in allowed}
    # Profiles authorize a wildcard; the signed executable requests a concrete service array.
    entitlements["com.apple.developer.icloud-services"] = ["CloudDocuments"]
    entitlements["com.apple.developer.icloud-container-environment"] = "Development"
    if platform == "macos":
        entitlements["com.apple.security.app-sandbox"] = True
    entitlement_path = output / "probe.entitlements"
    entitlement_path.write_bytes(plistlib.dumps(entitlements))
    sdk = "macosx" if platform == "macos" else "iphoneos"
    sdk_path = subprocess.check_output(["xcrun", "--sdk", sdk, "--show-sdk-path"], text=True).strip()
    rust_target = "aarch64-apple-darwin" if platform == "macos" else "aarch64-apple-ios"
    swift_target = "arm64-apple-macosx15.7" if platform == "macos" else "arm64-apple-ios18.0"
    library = output / "libprobe.a"
    commands = [
        ["rustc", "--edition=2021", "--crate-type=staticlib", "--target", rust_target,
         str(ROOT / "tests/apple-probe/probe.rs"), "-o", str(library)],
        ["xcrun", "--sdk", sdk, "swiftc", "-parse-as-library", "-sdk", sdk_path, "-target", swift_target,
         str(ROOT / "frontend/src-tauri/apple/AppleFiles.swift"), str(ROOT / "tests/apple-probe/Probe.swift"),
         str(library), "-o", str(executable_dir / "KeikeuProbe")],
        ["codesign", "--force", "--sign", certificate, "--entitlements", str(entitlement_path), str(app)],
        ["codesign", "--verify", "--strict", str(app)],
    ]
    with (output / "build.log").open("w") as log:
        for index, command in enumerate(commands, 1):
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=log)
            if result.returncode:
                raise SystemExit(f"{platform} build step {index} failed; inspect {output / 'build.log'}")
    print(f"{platform}: compiled and signature verified: {app}")
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("macos", "ios"))
    build(parser.parse_args().platform)
