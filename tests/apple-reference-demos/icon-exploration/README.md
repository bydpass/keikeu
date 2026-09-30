# 三个参考入口 demo 的图标

采用 ai-icon-studio 的 icon-design、art-direction、icon-composer 指引，以内置 `image_gen` 分别生成三枚原创 raster 概念。产品用途是帮助创作者在手机写作时查阅预选灵感；三个包仅测试不同系统入口，不替换正式 keikeu 标识。

- `snippet-1024.png`：米白纸卡与蓝色字段。
- `island-1024.png`：珊瑚色背景与深色胶囊。
- `fusion-1024.png`：紫色背景，蓝白纸卡与浅色胶囊组合。

每枚 `*-original.png` 保留工具返回的原始生成图；`*-prompt.txt` 保存精确输入。工具实际输出为 1254 × 1254，通过系统 `sips` 缩为 1024 × 1024，不重绘内容。三份 1024 PNG 均无 alpha、无预置平台圆角遮罩，可作为标准 AppIcon 输入。未生成 Composer `.icon`、图层或原生深色外观。

已查看原图及真实 32px 缩图，并在 `review.html` / `review.png` 对照明暗环境。三枚色彩和轮廓可区分；Snippet 折角在小尺寸较弱，但蓝色字段可辨；Island 最简明，但图形也容易被理解为开关；Fusion 的组合轮廓仍可读。明暗环境只是背景对照，不是系统 Dark appearance 验证。

内置工具成功调用三次，未使用外部付费 API。工具没有返回金额或用量价格，费用未知，不能宣称免费。AppIcon 编译、系统遮罩与设备显示由主代理集成验收。
