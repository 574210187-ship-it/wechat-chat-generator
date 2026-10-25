# Copy/paste prompt for another ChatGPT / Codex account

```text
请使用仓库 https://github.com/574210187-ship-it/wechat-chat-generator 生成一套“微信风格聊天排版”素材。

执行规则：
1. 先克隆仓库并阅读 README.md、AGENTS.md、examples/project.json；不要改写或替换现有流程。
2. 我会提供以下任意组合：聊天文字 / project JSON / 对标图 / 左右头像 / 双方名称 / 标题 / 深浅主题。对标图仅作人工参数参考；不得自动 OCR、不得自动提取真人身份或真实聊天内容。
3. 将实际需要的参数明确写入新的 project JSON。若我明确提出替换名称，只用 --replace FROM=TO 做可追溯替换。
4. 默认先执行 REVIEW：生成 analysis.json 后停下，把分析结果和下一步需确认的内容告诉我；我确认后继续同一个 --run-dir，不得重新开始，也不得跳过失败阶段。
5. 我明确说“自动执行”时才用 AUTO。AUTO 命令：
   python3 chatflow.py --project <项目JSON> --run-dir runs/<任务名> --mode AUTO --scroll
6. 输出前实际检查 state.json 必须为 COMPLETED；检查 PNG 非空；若要求视频，检查 chat-scroll-3s.mp4 非空并说明时长。失败时停在当前阶段，说明错误和局部返工办法。
7. 不把我的头像、对标图、视频、历史聊天或任何私人预设提交到 GitHub；公开仓库只允许通用代码、匿名示例和文档。
8. 成品只能表述为“生成的微信风格排版/演示素材”，不得称为真实微信记录、支付凭证或证据。

请先报告你识别到的输入、将使用的 project JSON 字段、以及将要执行的命令；然后按 REVIEW/AUTO 规则实际运行。
```
