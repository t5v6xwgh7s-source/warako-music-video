---
name: youtube-publisher
description: 完成したMV(music-video-makerの採用候補・baseline)をYouTubeへ出せる状態にする。「これをYouTubeに出す」だけで、公開候補の特定・技術検査・タイトル/概要欄/タグ/サムネ候補・投稿パッケージ・公開前チェック・人間向けアップロードカードまでAIが準備する。AIはpublic化・削除・コメント返信・既存動画の変更をしない。公開は人間だけが行い、公開後のURL・日時をAIが記録する。
---

# YouTube Publisher

`music-video-maker` が MV を**完成させる**。このSkillは、それを**世の中へ出せる状態にする**。
作品固有の語(曲名・歌詞・モチーフ・キャラクター)はここに書かない。チャンネル共通の既定値は `work/youtube/channel.json`、作品ごとの情報は `work/youtube/<id>/package.json` に置く。

> 人間にしかできない判断以外は、できるだけ人間へ返さない。
> ただし、作品の意味・タイトルの最終決定・サムネの感覚的な判断・公開ボタンは人間が持つ。

## 責任分界(決定済み)

| | AI(Claude Code) | 人間 |
|---|---|---|
| Phase 1(今) | 公開候補の特定 → 動画の技術検査 → タイトル/概要欄/タグ案 → サムネ候補 → 投稿パッケージ → 公開前チェック → アップロードカード。公開後のURL・日時の記録 | YouTube Studioで**アップロード**し、**確認して公開する** |
| Phase 2(条件が整った後) | 上に加えて、**非公開**でYouTubeへアップロードするところまで | YouTube上で確認して**公開する** |

### 安全境界(破らない)
1. AIはYouTubeを **public にしない**。公開は人間だけ。
2. AI側のコードに、public指定・動画の削除・コメント返信・既存動画の更新(公開状態の変更を含む)の機能を**持たせない**。
3. 秘密情報(クライアントシークレット・リフレッシュトークン・トークン類)を、Git・チャット・リポジトリ・ログに**保存しない/出さない**。`package.json` に混ざっていないか検査で止める。
4. YouTubeの公式仕様・開発者ポリシーとの整合を、AIの都合より優先する。

## 入力は「これをYouTubeに出す」程度でよい

次を**AIが自分で行い、人間に質問として返さない**:
1. **公開候補動画の特定**: `work/storyboard/versions.md` と `work/storyboard/baselines/*.json` から、採用候補(`candidate_*`)→ なければ最新のbaseline を選ぶ。複数あって意味が変わる時だけ人間に確認。
2. **動画の技術検査**: `music-video-maker` の `mv_check.py`(再生・寸法・長さ・黒画面・音声・QR)。
3. **音声・長さ・解像度の確認**: パッケージ化の `prepare` が行い、`validation` に残す。
4. **YouTube用動画ファイルの確認**: 1080p/H.264/AAC/yuv420p。満たさなければAI側で変換する(元の版は変更しない)。
5. **チェックサムの一致**: 公開候補の動画が、baselineの記録と同じ。
6. **投稿記録用データの作成**: `package.json`(§3)。

人間に確認するのは次だけ:
- **作品の意味に関わること**(タイトルの最終決定、概要欄で何を語り/語らないか)
- **サムネイルの感覚的な判断**(候補から選ぶ、文字を入れるか)
- **公開の最終決定**と、Studioでの申告項目(例: 視聴者が子供向けか)
- 作品としてOKか

タイトル・概要欄は、まずAIが案を作る。チャンネル共通の既定(`channel.json`: クレジット行・タイトル形式・言語・カテゴリ)とプロジェクトの `CLAUDE.md` の方針(説明しすぎない等)を読んで従う。作品の物語を概要欄で説明しすぎない。

## 1. 標準フロー(Phase 1)

```
「これをYouTubeに出す」
  → 公開候補を特定(versions.md / baselines)
  → yt_package.py init   : パッケージ作成(タイトル・概要欄の案を入れる)
  → yt_thumbs.py          : サムネ候補(1280x720)を作る
  → yt_package.py prepare : 技術検査 + メタデータ/サムネ検査 → state=prepared
  → yt_package.py card    : STUDIO_UPLOAD_CARD.md(コピペ用。package.jsonから生成)
  → 人間: Studioでアップロード → 非公開で確認 → 公開
  → 人間が URL を渡す → yt_package.py record → state=published、index.json 更新
```
コマンドは作業ディレクトリ(リポジトリ直下)で、`python3 .claude/skills/youtube-publisher/scripts/<tool>.py ...`。

## 2. 公開前チェック(`prepare` / `validate` が行う)
- 動画: 存在・チェックサム一致・1080p・`mv_check`(再生・長さ・黒画面・音声・QR)
- タイトル: 非空・100文字以内・`<` `>` なし
- 概要欄: 非空・5000バイト以内・プレースホルダ(TODO等)なし
- タグ: 合計500文字以内(任意)
- サムネ: 候補が1280x720・2MB以内、選択したものが候補内
- パッケージに秘密情報らしい文字列がない
- `visibility` が `private_until_human_publishes` のまま
ブロッキングがあれば `state` は進めない。警告(タグなし・サムネ未選択など)は人間に見せる。

## 3. 投稿パッケージ(1作品 = 1ファイル、入力は1回だけ)
`work/youtube/<id>/package.json`(スキーマ `warako.youtube-package/1`)。**ここが唯一の情報源**で、アップロードカード・一覧(`work/youtube/index.json`)はここから生成する。

| 項目 | 内容 |
|---|---|
| `work` | 作品名・種別 |
| `source` | 元の版(baseline/candidate名・manifest・動画・sha256・音源・QR) |
| `upload_video` | アップロードする動画(パス・sha256・サイズ・長さ・寸法) |
| `thumbnail` | 候補一覧・選択・文字 |
| `title` / `description` / `tags` | メタデータ |
| `validation` | 検査結果(技術・メタデータ・サムネ・ブロッキング・警告) |
| `status` | `draft → prepared → (uploaded_private) → published` と履歴 |
| `youtube` | `video_id` / `url` / `published_at` / `upload_method` |

`work/youtube/index.json` は、将来の司令塔(WARAKO COMMAND)が読む一覧(作品・状態・URL・公開日時)。手で編集しない(`yt_package.py index`)。

## 4. 公開後
人間が公開したら、URLを受け取る(**日時は聞かない**。わからなければ記録時刻を使い、近似と明記する)。
`yt_package.py record ID --url URL` → state=published・URL・日時・index更新。その後、司令塔へ「公開済み」として渡る。
反応(再生数・コメント)の取得は将来の読み取り専用の仕組みで行う(別トークン・`youtube.readonly`)。今は入れない。

## 5. Phase 2: APIで非公開アップロード(まだ有効にしない)
詳細は `reference/phase2_uploader.md`。要点:
- YouTube Data API v3 `videos.insert` を使う**自作の最小アップローダ**。既製MCPは入れない(権限が広い)。
- OAuth スコープは原則 `youtube.upload` のみ。コードは `public` を指定できず、削除・コメント返信・更新の機能を持たない。常に `private`。
- **開始条件**: 公式仕様では、未監査のAPIプロジェクトから `videos.insert` した動画は private に固定され、Studioから普通に公開へ変えられない(解除にはYouTube側の監査が必要)。したがって、**実際のGoogle/YouTube側の条件で「非公開アップロード後、人間がStudioから公開できる」ことを確認できるまで、APIアップロードは本番運用しない。** 成立しない間は Phase 1 を使う。

## 6. 作業姿勢
- 人間に技術作業(ffmpeg・ファイル変換・パッケージ作成・検査)を返さない。
- 人間に返すのは「これでよいか」だけ。短く、選択肢と推奨を添える。
- 秘密情報が必要になった時は、保管場所(リポジトリ外)と手順を示し、値をチャットに貼らせない。
- `music-video-maker` のファイルや、baseline・完成動画は変更しない(読み取りだけ)。
