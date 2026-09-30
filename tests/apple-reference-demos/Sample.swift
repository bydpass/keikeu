enum ReferenceSample {
    static let pages = [
        "她在等一个不会回来的人。\n表面目标：寄出这封信。\n真实愿望：有人告诉她，不必再等。",
        "雨声忽然停了，她却没有抬头。\n先写灯光，再写脚步。\n把答案留在门外，让读者先听见它。",
        "长页观察 · 合成内容\n一、先写房间里的声音。\n二、让人物停在门边。\n三、不急着解释来意。\n四、用一个动作表示犹豫。\n五、留意窗外光线变化。\n六、把重要的物件放在桌上。\n七、让对话有一次停顿。\n八、不要替人物说出答案。\n九、把最后一句留给脚步声。\n十、这是本页末尾。",
    ]

    static func normalizedPage(_ value: Int) -> Int {
        let remainder = value % pages.count
        return remainder < 0 ? remainder + pages.count : remainder
    }

    static func nextPage(_ value: Int) -> Int {
        (normalizedPage(value) + 1) % pages.count
    }
}
