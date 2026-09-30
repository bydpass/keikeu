import SwiftUI
import UIKit

// Separate bundle and process from Ref Probe; volatile test text only.
struct SyntheticEditor: UIViewRepresentable {
    @Binding var text: String

    final class Coordinator: NSObject, UITextViewDelegate {
        var parent: SyntheticEditor
        init(_ parent: SyntheticEditor) { self.parent = parent }
        func textViewDidChange(_ textView: UITextView) {
            parent.text = textView.text
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> UITextView {
        let view = UITextView()
        view.font = .preferredFont(forTextStyle: .body)
        view.adjustsFontForContentSizeCategory = true
        view.delegate = context.coordinator
        view.accessibilityIdentifier = "synthetic-editor"
        view.accessibilityLabel = "合成输入区"
        view.textContainerInset = UIEdgeInsets(top: 16, left: 12, bottom: 16, right: 12)
        return view
    }

    func updateUIView(_ uiView: UITextView, context: Context) {
        context.coordinator.parent = self
        // The UIKit view owns in-flight IME composition; do not rewrite it.
    }
}

@main
struct ReferenceEditorApp: App {
    @State private var text = ""
    var body: some Scene {
        WindowGroup {
            VStack(alignment: .leading, spacing: 12) {
                Text("Ref Editor").font(.title2)
                Text("独立进程 · 合成输入 · 关闭后不保证保留").font(.caption)
                SyntheticEditor(text: $text)
                Text("已接收 \(text.count) 字符").monospacedDigit()
            }
            .padding()
        }
    }
}
