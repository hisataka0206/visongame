# Role
あなたはPythonとComputer Visionの専門家です。
「MediaPipe」と「OpenCV」を使用して、Webカメラを使った体感型ARゲームを作成してください。

# Product Goal
PCの内蔵カメラで人間の骨格を認識し、画面上から落ちてくる「バナナ」や「オレンジ」を手や体でキャッチするゲーム `body_catch_game.py` を実装してください。

# Libraries
- opencv-python
- mediapipe
- numpy
- random
- time

# Requirements
## 1. Camera & Display
- Webカメラ(index 0)を使用する。
- ユーザーが鏡のように感じるよう、映像を左右反転（ミラーリング）して表示する。
- 画面解像度は 1280x720 とする。

## 2. Skeleton Detection (VisionPose alternative)
- `mediapipe.solutions.pose` を使用して全身の骨格を検出する。
- 検出された骨格（ランドマーク）を画面上に描画する。
- 特に「右手首(Right Wrist)」と「左手首(Left Wrist)」の座標を、当たり判定に使用する。

## 3. Game Objects (Fruits)
- バナナ（黄色）とオレンジ（オレンジ色）のオブジェクトをクラスとして定義する。
- 形状は `cv2.circle` で描画する単純な円で良い（色は区別する）。
- **Spawn:** 画面上端（Y=0）のランダムなX座標から定期的に生成する。
- **Gravity:** 時間経過とともにY座標が増加し、落下する。
- 画面下端を超えたらオブジェクトを削除する。

## 4. Interaction (Catch)
- 「手首の座標」と「フルーツの座標」のユークリッド距離を計算する。
- 距離が一定以下（例: 50px）になったら「キャッチ」とみなし、以下を行う。
  - スコアを +1 加算する。
  - そのフルーツを画面から消去する。
  - キャッチした場所に短い視覚エフェクト（円が広がるなど）を表示する。

## 5. Game Loop & UI
- **Time Limit:** 制限時間は60秒（1分）。
- 画面左上に「Score」と「Time」を大きく見やすく表示する。
- 制限時間が0になったらゲームループを止め、画面中央に大きく「GAME OVER」「Final Score: X」を表示する。
- 'q'キーまたはESCキーでゲームを終了できるようにする。

## 6. Game Assets
- バナナとオレンジの画像を用意する。
- iconフォルダにあるbanana.pngとorange.pngを用いてください。
- banana.pngとorange.pngの中心座標に表示する。
- それぞれの画像をキャッチしたときに、その場所に短い視覚エフェクト（円が広がるなど）を表示する。
- ただし、iconフォルダ内に該当のファイルがない場合には、デフォルトとしてそれぞれ黄色とオレンジ色の円を表示する。

# Implementation Details
- コードは1つのPythonファイル（`body_catch_game.py`）にまとめてください。
- エラーハンドリング（カメラが見つからない場合など）を含めてください。
- 実行時に必要な `pip install` コマンドをコメントまたは説明に含めてください。
- 変数名やコメントは分かりやすく記述してください。

# Add Another Requirements
- 現在、両手があたり判定となっています。しかし、足先があたった場合には得点が２。頭があたった場合には得点が３になるようにしたいです
- バックミュージックとして、テクノ系の音楽が流れるようにしたいです
- 履歴機能を用意して、過去の得点をトップ10を記録するようにします。何月何日何時何分に取得出来たかを、最後のゲーム完了時に表示します
- また、qを押下すると終了しますが、rを押下するとゲームを再開できるようにします。
- ゲームの難易度を変更できるようにします。具体的には、UIを用意して以下を変更できるようにします。
  - 1. ゲームのプレイ時間
  - 2. 落ち物の数
  - 3. 落ち物の落下速度
  - 4. 落ち物の落下する方向（下方向、斜め方向、上方向）
- この要求を満たすために、スタート画面を用意し、ゲームスタート時はS、難易度設定はPを押下します。
- Game Over時のリスタート画面でも、再スタートはR、難易度設定はPとします。
- モードをさらに追加し、ストーリーモードとフリーモードと分けます。従来のゲームをフリーモードとします。
- ストーリーモードは全部で５つのフリーモードを組み合わせたものとなっており、１つのゲームをクリアするたびに難しくなります。クリアしたかどうかの判断基準はそのゲームの中で理論上獲得できる最高得点の60％以上の得点をゲット出来たこと、とします。
- ストーリーモードを自作できるように難易度調整を別途ユーザーが決められるような仕組みを作りたいです。

# Add Another Requirements for another device
- また、別のパソコンでプレイするためには、パソコンのカメラを用いてプレイするようにしたいです。こちらをウェブブラウザ上で実現できるようにしたいです。
- 上記を実現するにあたって、一定のフォルダを作成し、そちらのフォルダ毎別のPCに移して、そこにあるhtmlファイルを叩くことで実現できるようにしたいです。

---

# How to Play (Usage Instructions)

## 1. Python Native Version
推奨環境: Python 3.8+, Webカメラ

### Install Dependencies
```bash
pip install opencv-python mediapipe numpy pygame
```

### Run Game
```bash
python3 body_catch_game.py
```

### Controls
- **S**: Start Game
- **M**: Toggle Mode (Free / Story)
- **P**: Settings (Free Mode) / Level Editor (Story Mode)
- **Q / ESC**: Quit
- **R**: Restart (during Game Over)

## 2. Web Port Version
フォルダ: `web_dist/`

### 実行方法 (Local)
`web_dist` フォルダに移動し、ローカルサーバーを起動してください。
```bash
cd web_dist
python3 run_local.py
```
ブラウザが開き、ゲームがプレイできます。

### 別のPCでのプレイ
1. `web_dist` フォルダ全体を別のPCにコピーしてください。
2. 以下のいずれかのファイルをダブルクリック（または実行）して起動してください：
   - **Windows**: `start_game.bat`
   - **Linux/Mac**: `start_game.sh`（初回は実行権限が必要な場合があります）
3. ブラウザが自動的に開き、ゲームが開始されます。
   - ※Webカメラへのアクセス許可を求められた場合は「許可」を選択してください。
   - ※Pythonがインストールされていない場合は、ローカルサーバーが起動しません。その場合は `index.html` を直接開いて試すこともできますが、ブラウザのセキュリティ制限によりカメラが動作しない可能性があります。推奨はPython環境での実行です。


### PoC調査

* PoCの調査を行うためにユーザーのログをGAS上に記載するようにしたい。
GASのアドレスはこちら。
https://script.google.com/macros/s/AKfycbxeJqv6X1k6V3o9HkMGSe7I-Td0F0ry8MgN3_NtLkEn1aYfapXYND5nUYl8PCamvu8ANA/exec

* GASにどのキーを打ったのかを記載されるように以下のコードを参考にindex.htmlを修正してください。
// ▼ ゲームごとにここを変える
const GAME_NAME = "AvoidWall_v1"; 

// ... (SESSION_IDなどはそのまま) ...

function sendKeyLog(keyName, note = "") {
    fetch(GAS_URL, {
        // ... (省略) ...
        body: JSON.stringify({
            gameName: GAME_NAME, // ▼ ここでゲーム名を送信！
            key: keyName,
            note: note,
            session: SESSION_ID 
        })
    });
}
