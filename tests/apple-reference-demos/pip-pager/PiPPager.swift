import AVFoundation
import AVKit
import SwiftUI
import UIKit

// Ref PiP: isolated experiment, not product code. Fixed synthetic text is drawn
// into an AVSampleBufferDisplayLayer and shown by system Picture in Picture; the
// system skip controls are mapped to reading steps. No Vault, network,
// persistence, timers, or keep-alive beyond the PiP session itself.

enum PiPReferences {
    static let all: [(title: String, pages: [String])] = [
        ("三页合成参考", ReferenceSample.pages),
        ("单卡合成参考", ["换一份参考：只有这一张卡片。\n用来检查回主应用更换整份参考后，小窗是否刷新并回到第一屏。"]),
    ]
}

/// Frame calibration knobs, in pixels. The system scales this portrait frame
/// into its PiP window; tune after a device legibility check.
enum PiPFrame {
    static let width = 600
    static let height = 800
    static let inset: CGFloat = 32
    static let header: CGFloat = 64
    static let footer: CGFloat = 64
    static let bodyFontSize: CGFloat = 44
    static let metaFontSize: CGFloat = 26
    static let overlap: CGFloat = 60 // about one line repeats between screens
    static var bodyWidth: CGFloat { CGFloat(width) - inset * 2 }
    static var viewport: CGFloat { CGFloat(height) - inset * 2 - header - footer }
    static var step: CGFloat { viewport - overlap }
    /// Every frame is stamped here, the middle of the 24 h playback range.
    static let pausedTime = CMTime(value: 12 * 3600, timescale: 1)
}

/// Append-only device evidence in the app's Documents folder (JSON Lines),
/// copied off the phone with `devicectl device copy from`. Records only event
/// names, positions, counters, and system states; never author text.
enum EventLog {
    static func write(_ event: String, _ fields: [String: String] = [:]) {
        var record = fields
        record["event"] = event
        record["time"] = ISO8601DateFormatter().string(from: Date())
        guard let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
              var line = try? JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]) else { return }
        line.append(0x0a)
        let url = directory.appendingPathComponent("pip-events.jsonl")
        if !FileManager.default.fileExists(atPath: url.path) {
            FileManager.default.createFile(atPath: url.path, contents: nil)
        }
        // ponytail: best-effort evidence; a failed write loses one line, never app state.
        guard let handle = try? FileHandle(forWritingTo: url) else { return }
        defer { try? handle.close() }
        _ = try? handle.seekToEnd()
        try? handle.write(contentsOf: line)
    }
}

@MainActor
enum PiPRenderer {
    static func body(_ text: String) -> NSAttributedString {
        let paragraph = NSMutableParagraphStyle()
        paragraph.lineSpacing = 6
        return NSAttributedString(string: text, attributes: [
            .font: UIFont.systemFont(ofSize: PiPFrame.bodyFontSize),
            .foregroundColor: UIColor(red: 0.12, green: 0.13, blue: 0.15, alpha: 1),
            .paragraphStyle: paragraph,
        ])
    }

    static func bodyHeight(_ text: String) -> CGFloat {
        body(text).boundingRect(
            with: CGSize(width: PiPFrame.bodyWidth, height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            context: nil
        ).height.rounded(.up)
    }

    /// Draws one BGRA frame directly into a pixel buffer and wraps it as a
    /// display-immediately sample; nil means the frame was not produced.
    static func sample(header: String, text: String, offset: CGFloat, footer: String) -> CMSampleBuffer? {
        var pixelBuffer: CVPixelBuffer?
        let attributes = [
            kCVPixelBufferIOSurfacePropertiesKey: [:] as CFDictionary,
            kCVPixelBufferCGImageCompatibilityKey: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey: true,
        ] as CFDictionary
        guard CVPixelBufferCreate(kCFAllocatorDefault, PiPFrame.width, PiPFrame.height,
                                  kCVPixelFormatType_32BGRA, attributes, &pixelBuffer) == kCVReturnSuccess,
              let buffer = pixelBuffer else { return nil }

        CVPixelBufferLockBaseAddress(buffer, [])
        guard let context = CGContext(
            data: CVPixelBufferGetBaseAddress(buffer),
            width: PiPFrame.width, height: PiPFrame.height, bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue
        ) else {
            CVPixelBufferUnlockBaseAddress(buffer, [])
            return nil
        }
        // UIKit text drawing expects a top-left origin.
        context.translateBy(x: 0, y: CGFloat(PiPFrame.height))
        context.scaleBy(x: 1, y: -1)
        UIGraphicsPushContext(context)
        UIColor(red: 0.97, green: 0.95, blue: 0.91, alpha: 1).setFill()
        context.fill(CGRect(x: 0, y: 0, width: PiPFrame.width, height: PiPFrame.height))

        let meta: [NSAttributedString.Key: Any] = [
            .font: UIFont.monospacedDigitSystemFont(ofSize: PiPFrame.metaFontSize, weight: .medium),
            .foregroundColor: UIColor(red: 0.36, green: 0.38, blue: 0.42, alpha: 1),
        ]
        let inset = PiPFrame.inset
        (header as NSString).draw(at: CGPoint(x: inset, y: inset + 12), withAttributes: meta)
        let bodyTop = inset + PiPFrame.header
        let bodyRect = CGRect(x: inset, y: bodyTop, width: PiPFrame.bodyWidth, height: PiPFrame.viewport)
        context.saveGState()
        context.clip(to: bodyRect)
        body(text).draw(
            with: CGRect(x: inset, y: bodyTop - offset, width: PiPFrame.bodyWidth, height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            context: nil
        )
        context.restoreGState()
        UIColor(white: 0.8, alpha: 1).setFill()
        context.fill(CGRect(x: inset, y: bodyRect.maxY + 8, width: PiPFrame.bodyWidth, height: 2))
        (footer as NSString).draw(at: CGPoint(x: inset, y: bodyRect.maxY + 22), withAttributes: meta)
        UIGraphicsPopContext()
        CVPixelBufferUnlockBaseAddress(buffer, [])

        guard let format = try? CMVideoFormatDescription(imageBuffer: buffer),
              let sample = try? CMSampleBuffer(
                imageBuffer: buffer,
                formatDescription: format,
                sampleTiming: CMSampleTimingInfo(
                    duration: .invalid,
                    presentationTimeStamp: PiPFrame.pausedTime,
                    decodeTimeStamp: .invalid
                )
              ) else { return nil }
        return sample
    }
}

final class PiPLayerView: UIView {
    override class var layerClass: AnyClass { AVSampleBufferDisplayLayer.self }
    var displayLayer: AVSampleBufferDisplayLayer { layer as! AVSampleBufferDisplayLayer }
    /// Device finding (iPhone 17 Pro, iOS 27.0, 2026-09-29): a frame enqueued
    /// before the layer joins a window stays blank, so the owner re-renders here.
    var onAttach: (@MainActor () -> Void)?

    override func didMoveToWindow() {
        super.didMoveToWindow()
        if window != nil { onAttach?() }
    }
}

@MainActor
final class PiPPager: NSObject, ObservableObject {
    @Published private(set) var referenceIndex = 0
    @Published private(set) var position = ReaderPosition()
    @Published private(set) var status = "尚未开始"
    @Published private(set) var isActive = false
    @Published private(set) var isPossible = false
    @Published private(set) var systemForward = 0
    @Published private(set) var systemBackward = 0
    @Published private(set) var playRequests = 0
    @Published private(set) var renderSize = "未报告"
    @Published private(set) var audioState = "未激活"
    /// True from a start tap until PiP starts or fails; the audio session is
    /// already active then, so the UI must still offer a way to cancel.
    @Published private(set) var pendingStart = false
    @Published var mixWithOthers = true

    let view = PiPLayerView()
    private var controller: AVPictureInPictureController?
    private var possibleObservation: NSKeyValueObservation?
    private var bodyHeights: [CGFloat] = []
    private var screenCounts: [Int] = []

    override init() {
        super.init()
        view.displayLayer.videoGravity = .resizeAspect
        // Device finding (Build 3, iOS 27.0): with no control timebase the layer's
        // clock sat outside the 24 h range, so the system disabled ⏩ and drew a
        // full progress bar. A timebase paused mid-range keeps both skip buttons
        // enabled; it carries no reading position.
        if let timebase = try? CMTimebase(sourceClock: .hostTimeClock) {
            try? timebase.setTime(PiPFrame.pausedTime)
            try? timebase.setRate(0)
            view.displayLayer.controlTimebase = timebase
        }
        measure()
        render()
        view.onAttach = { [weak self] in
            EventLog.write("layer_attached")
            self?.render()
        }
        let supported = AVPictureInPictureController.isPictureInPictureSupported()
        EventLog.write("launch", [
            "os": UIDevice.current.systemVersion,
            "build": Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "?",
            "pipSupported": String(supported),
            "renderer": Self.rendererPath,
        ])
        guard supported else {
            status = "此设备不支持画中画"
            return
        }
        let source = AVPictureInPictureController.ContentSource(
            sampleBufferDisplayLayer: view.displayLayer, playbackDelegate: self)
        let controller = AVPictureInPictureController(contentSource: source)
        controller.delegate = self
        // Default is already false; stated because auto-start on backgrounding
        // would open the window without an explicit tap.
        controller.canStartPictureInPictureAutomaticallyFromInline = false
        possibleObservation = controller.observe(\.isPictureInPicturePossible, options: [.initial, .new]) { [weak self] _, change in
            let possible = change.newValue ?? false
            Task { @MainActor in self?.possibleChanged(possible) }
        }
        self.controller = controller
    }

    var screenCount: Int { screenCounts.indices.contains(position.page) ? screenCounts[position.page] : 1 }

    func select(_ index: Int) {
        guard PiPReferences.all.indices.contains(index) else { return }
        referenceIndex = index
        position = ReaderPosition()
        measure()
        render()
        EventLog.write("select_reference", ["index": String(index), "pipActive": String(isActive)])
    }

    /// Explicit user action only; the audio session is touched here, never at launch.
    func start() {
        guard let controller else {
            status = "此设备不支持画中画；请回到应用内翻看后返回编辑器"
            return
        }
        guard !controller.isPictureInPictureActive else { return }
        EventLog.write("start_tap", ["mixWithOthers": String(mixWithOthers), "possible": String(controller.isPictureInPicturePossible)])
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: mixWithOthers ? [.mixWithOthers] : [])
            try session.setActive(true)
            audioState = mixWithOthers ? "已激活（混音）" : "已激活（独占）"
            EventLog.write("audio_active", audioFields())
        } catch {
            status = "音频会话未能启用，未启动小窗：\(error.localizedDescription)"
            EventLog.write("audio_error", ["error": error.localizedDescription])
            return
        }
        render()
        pendingStart = true
        if controller.isPictureInPicturePossible {
            beginPendingStart()
        } else {
            status = "等待系统允许启动小窗…"
        }
    }

    func stop() {
        pendingStart = false
        if let controller, controller.isPictureInPictureActive {
            controller.stopPictureInPicture()
        } else {
            releaseAudio("已取消")
        }
    }

    /// `fromSystem` separates PiP skip callbacks from the in-app preview buttons,
    /// so the counters only ever prove system events.
    func step(forward: Bool, fromSystem: Bool) {
        position = ReaderStep.move(position, forward: forward, screenCounts: screenCounts)
        if fromSystem {
            if forward { systemForward += 1 } else { systemBackward += 1 }
            // appState "background" proves the press arrived while another app was in front.
            EventLog.write("skip", ["forward": String(forward), "page": String(position.page + 1),
                                    "screen": String(position.screen + 1), "appState": Self.appState])
        }
        render()
    }

    static var rendererPath: String {
        if #available(iOS 17.0, *) { return "sampleBufferRenderer" }
        return "layer-enqueue"
    }

    private static var appState: String {
        switch UIApplication.shared.applicationState {
        case .active: "active"
        case .inactive: "inactive"
        case .background: "background"
        @unknown default: "unknown"
        }
    }

    private func audioFields() -> [String: String] {
        let session = AVAudioSession.sharedInstance()
        return ["category": session.category.rawValue,
                "mixWithOthers": String(session.categoryOptions.contains(.mixWithOthers)),
                "otherAudioPlaying": String(session.isOtherAudioPlaying)]
    }

    private func measure() {
        bodyHeights = PiPReferences.all[referenceIndex].pages.map(PiPRenderer.bodyHeight)
        screenCounts = bodyHeights.map {
            ReaderStep.screenCount(bodyHeight: $0, viewport: PiPFrame.viewport, step: PiPFrame.step)
        }
    }

    private func render() {
        let reference = PiPReferences.all[referenceIndex]
        let page = min(position.page, reference.pages.count - 1)
        let offset = ReaderStep.offset(screen: position.screen, bodyHeight: bodyHeights[page],
                                       viewport: PiPFrame.viewport, step: PiPFrame.step)
        let next = position.screen + 1 < screenCount ? "下一屏" : "下一页"
        guard let sample = PiPRenderer.sample(
            header: "\(reference.title) · 页 \(page + 1)/\(reference.pages.count)",
            text: reference.pages[page],
            offset: offset,
            footer: "屏 \(position.screen + 1)/\(screenCount) · 前进键：\(next) · 事件 \(systemForward + systemBackward)"
        ) else {
            status = "未能生成小窗画面；保留上一帧"
            EventLog.write("render_failed")
            return
        }
        // Every frame shares the paused timestamp, so flush (which keeps the
        // shown image and also clears a failed state) before each enqueue.
        // iOS 17 moved enqueueing to `sampleBufferRenderer`; iOS 15–16 only have
        // the layer-level calls, and the header forbids mixing the two paths.
        if #available(iOS 17.0, *) {
            let renderer = view.displayLayer.sampleBufferRenderer
            renderer.flush()
            renderer.enqueue(sample)
        } else {
            let layer = view.displayLayer
            layer.flush()
            layer.enqueue(sample)
        }
    }

    private func possibleChanged(_ possible: Bool) {
        isPossible = possible
        EventLog.write("possible", ["value": String(possible)])
        if possible, pendingStart { beginPendingStart() }
    }

    private func beginPendingStart() {
        pendingStart = false
        status = "已请求启动小窗"
        EventLog.write("start_requested")
        // Next main-loop turn, after the first frame is enqueued.
        Task { @MainActor in self.controller?.startPictureInPicture() }
    }

    private func releaseAudio(_ reason: String) {
        do {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            status = reason
            audioState = "已释放"
            EventLog.write("audio_released", audioFields().merging(["reason": reason]) { $1 })
        } catch {
            status = "\(reason)；音频会话释放失败：\(error.localizedDescription)"
            audioState = "释放失败"
            EventLog.write("audio_release_error", ["reason": reason, "error": error.localizedDescription])
        }
    }

    fileprivate func didStart() {
        isActive = true
        status = "小窗已启动：切到 Ref Editor，用小窗的后退/前进键逐屏阅读"
        EventLog.write("pip_started", ["appState": Self.appState])
        controller?.invalidatePlaybackState()
    }

    fileprivate func failedToStart(_ message: String) {
        isActive = false
        pendingStart = false
        EventLog.write("pip_failed", ["error": message])
        releaseAudio("小窗启动失败：\(message)")
    }

    fileprivate func didStop() {
        isActive = false
        EventLog.write("pip_stopped", ["appState": Self.appState])
        releaseAudio("小窗已退出；阅读位置仅保留到本进程结束")
    }

    fileprivate func playRequested() {
        playRequests += 1
        EventLog.write("play_request", ["appState": Self.appState])
        // Static content stays paused; this only restores the paused icon.
        controller?.invalidatePlaybackState()
    }

    fileprivate func renderSizeChanged(_ size: String) {
        renderSize = size
        EventLog.write("render_size", ["size": size, "appState": Self.appState])
    }
}

// AVKit does not document its callback thread, so every requirement is
// nonisolated and hops to the main actor before touching state.
extension PiPPager: AVPictureInPictureControllerDelegate, AVPictureInPictureSampleBufferPlaybackDelegate {
    nonisolated func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController) {
        Task { @MainActor in self.didStart() }
    }

    nonisolated func pictureInPictureController(_ controller: AVPictureInPictureController,
                                                failedToStartPictureInPictureWithError error: Error) {
        let message = error.localizedDescription
        Task { @MainActor in self.failedToStart(message) }
    }

    nonisolated func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController) {
        Task { @MainActor in self.didStop() }
    }

    nonisolated func pictureInPictureController(
        _ controller: AVPictureInPictureController,
        restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completionHandler: @escaping (Bool) -> Void
    ) {
        EventLog.write("restore_ui")
        completionHandler(true)
    }

    nonisolated func pictureInPictureController(_ controller: AVPictureInPictureController, setPlaying playing: Bool) {
        Task { @MainActor in self.playRequested() }
    }

    nonisolated func pictureInPictureControllerTimeRangeForPlayback(_ controller: AVPictureInPictureController) -> CMTimeRange {
        // ponytail: a fixed finite range only keeps the skip controls available;
        // it carries no reading position. UIPiPView #17 reports high CPU with
        // an infinite (live) range since iOS 16.1.
        CMTimeRange(start: .zero, duration: CMTime(value: 24 * 3600, timescale: 1))
    }

    nonisolated func pictureInPictureControllerIsPlaybackPaused(_ controller: AVPictureInPictureController) -> Bool {
        true
    }

    nonisolated func pictureInPictureController(_ controller: AVPictureInPictureController,
                                                didTransitionToRenderSize newRenderSize: CMVideoDimensions) {
        let size = "\(newRenderSize.width)×\(newRenderSize.height) px"
        Task { @MainActor in self.renderSizeChanged(size) }
    }

    nonisolated func pictureInPictureController(_ controller: AVPictureInPictureController,
                                                skipByInterval skipInterval: CMTime,
                                                completion completionHandler: @escaping () -> Void) {
        let forward = CMTimeGetSeconds(skipInterval) >= 0
        nonisolated(unsafe) let done = completionHandler
        Task { @MainActor in
            self.step(forward: forward, fromSystem: true)
            done() // AVKit requires this on every skip, or its controls stay "seeking".
        }
    }

    nonisolated func pictureInPictureControllerShouldProhibitBackgroundAudioPlayback(_ controller: AVPictureInPictureController) -> Bool {
        true // No audio is ever produced.
    }
}

struct PiPLayerHost: UIViewRepresentable {
    let view: PiPLayerView
    func makeUIView(context: Context) -> PiPLayerView { view }
    func updateUIView(_ uiView: PiPLayerView, context: Context) {}
}

@main
struct RefPiPApp: App {
    @StateObject private var pager = PiPPager()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            // NavigationView and plain rows keep one UI path from iOS 15 up;
            // NavigationStack and LabeledContent need iOS 16.
            NavigationView {
                Form {
                    Section("合成参考实验") {
                        Text("只显示固定合成文本，不读取或保存你的文稿，不联网。")
                        Text("小窗由系统画中画承载，窗口不接收拖动；只能用系统后退／前进键逐屏阅读，这不等于手指滚动。")
                    }
                    Section("1 选择参考") {
                        Picker("参考", selection: Binding(get: { pager.referenceIndex }, set: { pager.select($0) })) {
                            ForEach(PiPReferences.all.indices, id: \.self) { Text(PiPReferences.all[$0].title).tag($0) }
                        }
                        Text("更换整份参考在本页完成；小窗打开时更换，也回到第一屏。").font(.footnote)
                    }
                    Section("2 持续参考") {
                        // Actions first: on a small screen the preview must not
                        // push the start button below the fold (device finding).
                        Button("开始小窗") { pager.start() }
                            .disabled(pager.isActive || pager.pendingStart)
                        Button(pager.pendingStart ? "取消启动" : "退出小窗") { pager.stop() }
                            .disabled(!pager.isActive && !pager.pendingStart)
                        Toggle("与其他音频混合", isOn: $pager.mixWithOthers)
                            .disabled(pager.isActive || pager.pendingStart)
                        PiPLayerHost(view: pager.view)
                            .aspectRatio(CGFloat(PiPFrame.width) / CGFloat(PiPFrame.height), contentMode: .fit)
                            .frame(maxWidth: .infinity, maxHeight: 200)
                            .accessibilityLabel("小窗画面预览")
                        HStack {
                            Button("上一屏") { pager.step(forward: false, fromSystem: false) }
                            Spacer()
                            Text("应用内预览，不计入系统事件").font(.caption)
                            Spacer()
                            Button("下一屏") { pager.step(forward: true, fromSystem: false) }
                        }
                        .buttonStyle(.borderless)
                    }
                    Section("状态") {
                        Text(pager.status).accessibilityIdentifier("pip-status")
                        row("系统允许启动", pager.isPossible ? "是" : "否")
                        row("小窗前进／后退", "\(pager.systemForward)／\(pager.systemBackward)")
                            .accessibilityIdentifier("pip-skips")
                        row("中间播放键", "\(pager.playRequests) 次（未映射）")
                        row("小窗像素", pager.renderSize)
                        row("音频会话", pager.audioState)
                        row("系统与渲染", "iOS \(UIDevice.current.systemVersion) · \(PiPPager.rendererPath)")
                    }
                    Section("观察什么") {
                        Text("开始小窗后切到 Ref Editor，唤起手机原键盘并输入。分别记录：小窗是否持续可见、文字是否进入编辑器、前进／后退键是否换屏，以及小窗是否遮住正在输入的正文。")
                    }
                }
                .navigationTitle("Ref PiP")
            }
            .navigationViewStyle(.stack)
        }
        .onChange(of: scenePhase) { phase in
            EventLog.write("scene", ["phase": "\(phase)"])
        }
    }

    private func row(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
            Spacer()
            Text(value).foregroundColor(.secondary).multilineTextAlignment(.trailing)
        }
    }
}
