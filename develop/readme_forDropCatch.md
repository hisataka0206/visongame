# Torupose (Drop Catch Game) 仕様書

## 1. 概要 (Overview)
Webカメラを使用して、画面上から出現するフルーツ（バナナ、オレンジ）を体の動きでキャッチする体感型ARゲームです。
「MediaPipe Pose」を用いてブラウザ上で動作し、骨格検知を利用したインタラクションを行います。

## 2. システム構成 (Architecture)
- **プラットフォーム:** Webブラウザ (Chrome推奨)
- **技術スタック:**
  - **Core:** HTML5, CSS3, Vanilla JavaScript
  - **Vision:** MediaPipe Pose (CDN経由)
  - **Logging:** Google Apps Script (GAS) 連携によるPoCデータ収集

### ディレクトリ構造
- `base/` (ルート): Web版（本番/最新）
  - `index.html`: エントリーポイント
  - `game.js`: ゲームロジック
  - `style.css`: UIスタイル
  - `assets/`: 画像・音声リソース
  - `run_local.py`: ローカル実行用簡易サーバー
- `base/develop/`: Python Native版（プロトタイプ/旧版）

---

## 3. Web版 ゲーム仕様 (Game Specifications)

### 3.1 ゲームルール
- **目的:** 制限時間内に、出現するフルーツを体で触れてスコアを稼ぐ。
- **オブジェクト:**
  - **バナナ / オレンジ:** ランダムに出現。落下、または浮上（設定による）。
  - **更新方法:**
    - 特定のディレクトリに特定の名前で保存することでゲーム内のオブジェクトが更新される
- **スコア計算 (Body Parts Scoring):**
  部位によって獲得スコアが異なります。
  - **頭 (Head):** +3点
  - **足 (Feet):** +2点
  - **手 (Wrists):** +1点
- **演出:** キャッチ時にエフェクト（円）を表示し、フルーツは消滅する。

### 3.2 ゲームモード (Modes)
**Mキー** でモードを切り替えます。

#### 1. FREE MODE (フリーモード)
- 自由に設定（時間、速度、頻度、方向）を変更してプレイするモード。
- 初期設定は設定画面で変更可能。

#### 2. STORY MODE (ストーリーモード)
- 全5ステージを順にクリアしていくモード。
- **クリア条件:** そのステージで理論上獲得可能な最大スコアの **60%** 以上を獲得すること。
- **ステージ構成:**
  - Stage 1: ゆっくり落下
  - Stage 2: 標準速度
  - Stage 3: 斜め移動
  - Stage 4: 高速・斜め
  - Stage 5: "UP" (下から上へ浮上)
- **レベルエディタ:** Story Modeの設定画面で、各ステージの構成をカスタマイズ可能。

### 3.3操作方法 (Controls)

| 画面 | キー | 動作 |
| :--- | :--- | :--- |
| **共通** | `Q` / `Esc` | ゲーム終了 / タイトルへ戻る |
| **タイトル** | `S` | ゲームスタート |
| | `M` | モード切替 (Free ⇔ Story) |
| | `P` | 設定画面へ (Settings / Level Editor) |
| **設定画面** | `1` - `4` | 各項目の設定値を変更 |
| | `B` / `P` | タイトルへ戻る |
| | `,` / `.` | (Storyのみ) ステージ選択 (Prev/Next) |
| **プレイ中** | (なし) | 体で操作。キー入力は誤操作としてログ記録 |
| **GAME OVER** | `R` | リトライ (Story時は同じステージから、全クリア時は最初から) |
| | `P` | 設定画面へ |

### 3.4 設定項目 (Configuration)
設定画面 (`P`) で以下のパラメータを調整可能です。

1. **Game Duration:** ゲーム時間 (30s, 60s, 90s, 120s)
2. **Spawn Rate:** 出現頻度 (間隔: 0.3s ~ 1.5s)
3. **Speed Mult:** 落下速度倍率 (0.5x ~ 3.0x)
4. **Direction:** 移動方向
   - `Down`: 上から下へ落下
   - `Diagonal`: 斜めに落下・反射
   - `Up`: 下から上へ浮上

### 3.5 ログ収集機能 (PoC Logging)
Google Apps Script (GAS) へ以下の行動ログを送信します。
- **Key Press:** 押下されたキー
- **Erroneous Input:** 想定外のキー操作（プレイ中のキー操作など）
- **Game Events:** Game Over, Stage Clear (スコア、リトライ回数、到達ステージ)

---

## 4. 実行方法 (How to Run)

Webカメラを使用するため、ローカルサーバー経由での実行が必要です。

### 手順
1. `base/` ディレクトリに移動。
2. 以下のコマンドでサーバーを起動（Python環境がある場合）。
   ```bash
   python3 run_local.py
   ```
3. ブラウザで `http://localhost:8000` (または表示されるポート) にアクセス。

---

## 5. Python Native版 (Legacy)
`base/develop/body_catch_game.py` に配置されています。
OpenCV + MediaPipe (Python) で動作するデスクトップアプリ版です。
基本的なルールは同様ですが、Web版のようなストーリーモードや詳細な設定UIは実装が異なる場合があります。

### 実行方法
```bash
cd base/develop
pip install opencv-python mediapipe numpy
python3 body_catch_game.py
```