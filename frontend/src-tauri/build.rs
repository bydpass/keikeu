fn main() {
    let target = std::env::var("TARGET").unwrap();
    if target.contains("apple") {
        let ios = target.contains("ios");
        let simulator = target.ends_with("sim");
        let sdk = if simulator {
            "iphonesimulator"
        } else if ios {
            "iphoneos"
        } else {
            "macosx"
        };
        let arch = if target.starts_with("aarch64") {
            "arm64"
        } else {
            "x86_64"
        };
        let swift_target = if ios {
            format!(
                "{arch}-apple-ios18.0{}",
                if simulator { "-simulator" } else { "" }
            )
        } else {
            format!("{arch}-apple-macosx11.0")
        };
        let sdk_path = std::process::Command::new("xcrun")
            .args(["--sdk", sdk, "--show-sdk-path"])
            .output()
            .unwrap();
        assert!(sdk_path.status.success());
        let out = std::env::var("OUT_DIR").unwrap();
        let status = std::process::Command::new("xcrun")
            .args([
                "swiftc",
                "-parse-as-library",
                "-emit-library",
                "-static",
                "-module-name",
                "KeikeuNative",
                "-target",
                &swift_target,
                "-sdk",
                String::from_utf8(sdk_path.stdout).unwrap().trim(),
                "apple/Host.swift",
                "-o",
                &format!("{out}/libKeikeuNative.a"),
            ])
            .status()
            .unwrap();
        assert!(status.success(), "Apple host compilation failed");
        println!("cargo:rerun-if-changed=apple/Host.swift");
        let swift = std::process::Command::new("xcrun")
            .args(["--find", "swiftc"])
            .output()
            .unwrap();
        assert!(swift.status.success());
        let swift = String::from_utf8(swift.stdout).unwrap();
        let toolchain = std::path::Path::new(swift.trim())
            .parent()
            .unwrap()
            .parent()
            .unwrap();
        println!(
            "cargo:rustc-link-search=native={}/lib/swift/{sdk}",
            toolchain.display()
        );
        println!("cargo:rustc-link-search=native={out}");
        println!("cargo:rustc-link-lib=static=KeikeuNative");
        println!("cargo:rustc-link-lib=framework=Foundation");
        println!(
            "cargo:rustc-link-lib=framework={}",
            if ios { "UIKit" } else { "AppKit" }
        );
    }
    tauri_build::build()
}
