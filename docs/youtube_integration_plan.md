# YouTube 連携の検討(設計案。**まだ何も導入・アップロードしていない**)

2026-10-04。結論: 今回は**手動でStudioから公開**する(作品は完成済み)。連携は公開後に、最小権限の非公開アップロードから段階的に入れる。

## 1. 現在環境の確認(実測)

| 項目 | 結果 |
|---|---|
| 実行環境 | クラウドのコンテナ(使い捨て)。node 22 / npm 10 / `claude` CLI あり |
| MCP設定 | このリポジトリ・環境には**YouTube関連のMCPは未設定**(`claude mcp list` = なし) |
| ネットワーク | Google(`accounts.google.com`、`googleapis.com`)へ到達できる。ただし**OAuthの同意はブラウザ+`127.0.0.1`のリダイレクトが必要**で、このコンテナでは完結しない → 認可はローカルで行う |
| 秘密情報 | リポジトリ内に `.env` / token / client_secret の類いは**なし**(`git ls-files` で確認) |
| `.gitignore` | 秘密情報のパターンが**まだ無い** → 導入前に追加が必要(§6) |
| 動画 | 公開用の完成版あり(`output/final/candidate_v3d_r3_continuous/`、63MB / 送信用29MB) |
| 既存Skill | `music-video-maker`(今回は変更しない) |

## 2. 推奨する接続方式

案を3つ比べた。

| 案 | 内容 | 評価 |
|---|---|---|
| **A 手動(今回)** | Studioでアップロード → 公開 → URLをClaudeへ | 最も安全で速い。**今回はこれ** |
| **B 自作の小さなアップローダ(推奨・次)** | YouTube Data API v3 / OAuth 2.0。スコープは `youtube.upload` だけ。コードは `public` を指定できない作りにして**必ず非公開**で上げる。公開は人間がStudioで行う | 削除・公開・コメント返信の権限そのものが無い。人間の承認が構造で守られる |
| C `@m8lab/mcp-youtube` | Claude CodeのMCPとして、アップロード・更新・プレイリスト・統計・コメント | 便利だが権限が広い(下記) |

### `@m8lab/mcp-youtube` を実際に確認した結果
npmのtarball(v1.0.0)を取得して、コードを**実行せずに**読んだ。

- 良い点: コードは小さく読める(約47KB)。インストール時のスクリプト(postinstall)なし。Google API以外への通信なし。認証はenv変数。アップロードの既定は `private`。
- 注意: 単独の個人メンテナ・v1.0.0。**OAuthスコープが広い**(`youtube`(全管理)+`upload`+`force-ssl`)。
  ツールに `delete_video`(完全削除)、`update_video`(公開設定を `public` に変更できる)、`reply_comment` があり、`upload_video` にも `privacy: public` を渡せる。**人間の承認はパッケージ内にない**ので、使うなら承認はこちら側で強制する必要がある。
- 使うなら: バージョンを固定(1.0.0)、ローカルで実行、`delete_video` / `update_video` / `reply_comment` / `upload_video` は常に確認を求める設定にする、可能ならフォークして `public` と `delete` を削る。
- 統計・コメントの読み取りが目的になった段階では、`youtube.readonly` だけの別トークンにするほうが安全。

### 要確認(私の知識で、公式で確かめる必要がある点)
- **審査前のAPIプロジェクトからアップロードした動画は、非公開に固定される**ことがある(審査後に解除)。もしそうなら、API経由アップロード → Studioで公開、の流れが成立しない。**これが確認できるまで、今回は手動が正解。**
- 同意画面が「テスト」状態だと、リフレッシュトークンが約7日で失効することがある。

## 3. Google側で人間が一度だけ行う設定
(順子ちゃん本人のGoogleアカウント認証だけは代行できない。以外はClaudeが手順書を作る。)
1. Google Cloud Console で新規プロジェクトを作る(YouTube専用)。
2. 「YouTube Data API v3」を有効にする(統計を使うなら「YouTube Analytics API」も)。
3. OAuth同意画面を設定する(外部/テスト、自分のアカウントをテストユーザーに追加)。
4. OAuthクライアントIDを作る(種類: デスクトップアプリ)→ `client_secret.json` をダウンロード。
5. **ローカルのPCで**一度だけ認可スクリプトを実行し、ブラウザで同意 → リフレッシュトークンを得る。
6. 上記を秘密置き場(§5)へ保存。**チャットやGitには貼らない。**

## 4. Claude Code側で自動化できること
- アップローダ・認可スクリプト・メタデータ生成の作成とテスト(ドライラン)
- アップロード前の最終検査(`mv_check.py`)、ファイルの整合(チェックサム)
- タイトル・概要欄・タグ・サムネ候補の準備(§7のSkill)
- 非公開アップロード → URL(動画ID)取得 → 記録
- 公開後のURL・日時・数字の記録(司令塔の第1号データ)
- 権限設定(`.claude/settings.json` で該当ツールを常に確認)、`.gitignore` の更新
- 後から: 統計の取得(読み取り専用トークン)

## 5. 必要な秘密情報
| 名前 | 内容 | 保管 |
|---|---|---|
| `YOUTUBE_OAUTH_CLIENT_ID` | OAuthクライアントID | ローカルの秘密置き場 |
| `YOUTUBE_OAUTH_CLIENT_SECRET` | クライアントシークレット | 同上(Git禁止) |
| `YOUTUBE_REFRESH_TOKEN` | 認可後のリフレッシュトークン | 同上(Git禁止) |
| `YOUTUBE_CHANNEL_ID` | チャンネルID(秘密ではない) | 設定ファイル可 |

- 保管場所: リポジトリの**外**(例 `~/.config/warako/youtube.env`、権限600)か、OSのキーチェーン。`.mcp.json` にはenv変数の参照だけを書き、値は書かない。
- クラウドのセッションに渡すより、**ローカルのClaude Code**で使うほうが安全。

## 6. `.gitignore` の変更案(未適用)
```gitignore
# Secrets (YouTube / Google OAuth etc.) - never commit
.env
.env.*
*.env
client_secret*.json
credentials*.json
*refresh_token*
*.token
.youtube/
secrets/
.config/
```
あわせて、導入時に `git ls-files | grep -iE "secret|token|\.env"` が空であることを確認し、`git secrets` 相当の簡易チェック(pushの前に秘密情報らしい文字列を検出)をスクリプトにする。

## 7. `youtube-publisher` Skill の設計案
`music-video-maker` と同じく、**作品固有の語は入れない**。作り方だけを持つ。

流れ:
```
完成版(baselineまたは採用候補)
  → 最終検査(mv_check.py)
  → 投稿セット作成: タイトル候補 / 概要欄 / タグ / サムネ候補 / 公開設定(= 常に非公開)  [作品の語はプロジェクトの文書から読む]
  → 人間が確認(作品としてOKか)
  → 非公開でアップロード(dry-runを先に)
  → 人間がYouTube上で確認
  → 人間が公開(Studio)   ← AIは公開しない
  → 公開URL・日時を記録(司令塔へ)
  → (後で)統計の取得
```
原則:
- 公開(public)・削除・コメント返信は**人間の明示的な承認がある時だけ**。アップローダは構造上 `private` 固定。
- 秘密情報をチャット・Git・ログに出さない。
- 人間に返すのは、作品としての可否・サムネ/タイトルの好み・公開の最終決定だけ。技術作業は返さない。
- 公開の経験(今回の手動公開で詰まった点)を、このSkillの仕様に反映してから作る。

置くもの(案): `.claude/skills/youtube-publisher/SKILL.md`、`scripts/yt_prepare.py`(投稿セット検査・整形)、`scripts/yt_upload.py`(非公開固定・dry-run)、`scripts/yt_record.py`(URL・日時の記録)。記録先は司令塔の「作品」データ(1作品=1ファイル: 公開先・URL・日付・数字・次の行動)。

## 8. 順番(提案)
1. **今**: 手動で公開 → URLをClaudeへ(サムネは仮で公開し、あとから差し替える)。
2. URLを司令塔の第1号データ(この作品)として記録。
3. 司令塔の骨組み(入口 → 次の行き先 → 価値交換の導線、数字は後から自動化)。
4. 手動公開で見えた手順を元に `youtube-publisher` Skill。
5. 上の「要確認」を公式で確認 → 問題なければBの非公開アップローダ → (必要なら)読み取り専用の統計。
6. 導線が整ってから Shorts / Reels / TikTok。
