# YouTube 公開メモ(第1号: 虹の向こうで会いたい)

**この文書に、タイトル・概要欄などの内容は書かない**(二重管理を避ける)。唯一の情報源は
`work/youtube/niji-no-mukou-de-aitai/package.json`。人間向けのコピペカードは同じフォルダの `STUDIO_UPLOAD_CARD.md`(自動生成)。

- 公開に使う版: `candidate_v3d_r3_continuous`(`work/storyboard/versions.md`)
- サムネ候補: `work/youtube/niji-no-mukou-de-aitai/thumbnails/`(3案。選ぶのは人間)
- 方針: 宣伝しない / Shorts・Reels・TikTok は導線が整ってから / QRは概要欄で説明しない
- 手順と責任分界: `.claude/skills/youtube-publisher/SKILL.md`(Phase 1: 人間がStudioでアップロードして公開)
- APIでの非公開アップロード(Phase 2): `.claude/skills/youtube-publisher/reference/phase2_uploader.md`(条件が整うまで使わない)
- 連携の調査: `docs/youtube_integration_plan.md`

公開したら、URLをClaudeへ渡す。記録は `yt_package.py record` が行う(公開URL・日時は package.json と `work/youtube/index.json` に入る)。
