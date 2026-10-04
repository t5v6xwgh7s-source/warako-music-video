# Phase 2 設計: 最小のYouTubeアップローダ(未実装・未有効)

## 目的と境界
- AI: 公開候補を **非公開(private)でYouTubeへアップロードする**ところまで。
- 人間: YouTube上で確認して**公開**する。AIは公開しない。
- 既製MCPは入れない。必要最小限の自作。

## 開始条件(すべて満たすまで本番運用しない)
1. **監査ロックの確認**: 公式資料(YouTube Data API `videos` / `videos.insert` の制限事項)を、その時点の最新で確認する。未監査(2020-07-28以降に作成)のAPIプロジェクトから `videos.insert` した動画はprivateにロックされ、公開に変えられない、とされている。
2. **実地の確認**: 小さなテスト動画を**非公開**でAPIからアップロード → **人間がStudioで公開に変更できる**ことを確認(できないならロックされている)。この確認自体は人間のStudio操作が要る。
3. 成立しない場合: YouTubeの監査(API Services Audit)の申請を行うか、Phase 1(手動Studio)を続ける。**成立するまでAPIアップロードを本番に使わない。**
4. OAuthの同意画面が「テスト」状態でないこと、またはリフレッシュトークンの失効(約7日)への対処(要確認)。
5. 秘密情報の保管場所がリポジトリ外であること(`.gitignore` と秘密検査が有効)。

## 設計
| 項目 | 内容 |
|---|---|
| API | YouTube Data API v3 `videos.insert`(再開可能アップロード) |
| スコープ | `https://www.googleapis.com/auth/youtube.upload` のみ |
| 認可 | デスクトップアプリ向けOAuth 2.0。認可は**人間がローカルで一度だけ**。リフレッシュトークンはリポジトリ外に保管 |
| 入力 | `work/youtube/<id>/package.json`(`validation.ok` が真・`state=prepared`) |
| 出力 | `youtube.video_id`・`state=uploaded_private`・`upload_method=api-private`、履歴に時刻 |
| 固定 | `privacyStatus` は `"private"` をコードに固定。引数で変えられない。`selfDeclaredMadeForKids` 等の申告は人間が行う(AIは決めない) |
| 持たない機能 | public指定、削除(`videos.delete`)、更新(`videos.update`)、コメント(`comments.*`)、プレイリスト操作 |
| 事前 | `--dry-run`(送信しない)を既定にし、`--confirm-private-upload` を明示した時だけ送信 |
| サムネ | `thumbnails.set` は別スコープ(`youtube` 系)が要るため、**使わない**。サムネは人間がStudioで設定(カードに記載) |
| 秘密検査 | 送信前に、パッケージとログに秘密情報が出ないことを確認 |
| 失敗時 | 中断・再開可能。重複アップロードを防ぐため、送信前に `youtube.video_id` が空であることを確認 |

## 環境変数(値はリポジトリの外)
`YOUTUBE_OAUTH_CLIENT_ID` / `YOUTUBE_OAUTH_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN`。例: `~/.config/warako/youtube.env`(権限600)。

## 公開後
人間が公開 → URLを受け取り `yt_package.py record`(`upload_method` は `api-private` と記録)。反応の取得は別の読み取り専用トークン(`youtube.readonly`)で、Phase 2の後。
