# 動作風景

![](appendix/SharingVideo.1.ss=27.gif)

プレイ画面の左側には，車の状態やMPPI介入御器の動作時間がリアルタイムで表示されている．
右側には，ステアリング角度がリアルタイムで表示されている．背景色が緑色の時は介入が入っておらず，赤色の時には介入が入っていることを示している．
MPPI介入制御器は路上に現れるATMへの衝突を回避するように動作している．

* [フル尺動画](https://drive.google.com/file/d/182SZXDYqLQDjGrhetzwWtKFgwt4GD0wb/view?usp=sharing)

# 必要なもの
* **[Astral uv](https://docs.astral.sh/uv/)**：Pythonの仮想環境とプロジェクト管理アプリ．
* **[CARLA 0.10.x](https://carla.org/)**：研究用の車ゲーム．必ず0.10.x系バージョンを使うように．例えば[ここ](https://github.com/carla-simulator/carla/releases/tag/0.10.0)からダウンロードできる．
* **Logitech G29 Driving Force Racing Wheel & Pedals**：人からの車操作を受け付ける筐体．無ければ別の手段を通じて人入力を作る必要がある．

# インストール
### 1. 外部依存ライブラリを持ってくる
このプロジェクトをクローンし，`Dependencies`というフォルダを作る．このフォルダの中に**2つ**のライブラリファイルを入れる．

1つ目は，G29と通信するためのライブラリファイルである．
[LogicoolのHP](https://gaming.logicool.co.jp/ja-jp/innovation/developer-lab.html)から"ステアリングホイールSDK"をダウンロードし，この中の次の場所にあるライブラリファイルを`Dependencies`へ入れる．
```bash
Lib/GameEnginesWrapper/x64/LogitechSteeringWheelEnginesWrapper.dll
```
このライブラリファイルは本来はC++で使うものだが，同著者が作成した[LogitechSteeringWheelPy](https://github.com/Mya-Mya/LogitechSteeringWheelPy)がPythonからの使用を可能にしている．

2つ目は，CARLAと通信するためのライブラリファイルである．ダウンロードしたCARLAのフォルダの中の
```bash
PythonAPI/carla/dist
```
から，使用するPythonバージョンに合った`.whl`ファイルを`Dependencies`へ入れる．

### 2. Python仮想環境を作る
```bash
uv sync
```

### 3. ゲームの準備をする
* CARLAを起動する．
* G29をコンピューターに接続する．

### 4. ゲームを始める
`gaming.py`が本プログラムである．
```bash
uv run gaming.py
```


# コードの説明
### gaming.py
* PyGameゲームエンジンの管理
* GUIの表示
* 車の状態や制御器の動作，ゲームシステムの状態の記録
* G29との通信の樹立
* 車，車載カメラ，障害物の設置と管理
* ゲームループの実行
* 制御器の動作と制御の実行

### mppi.py
この中の`MPPIFilter`では，モデル予測経路積分制御（MPPI）を実装している．NumPyの並列計算機能を駆使して，高速で動作するように作っている．
### keepoutareas.py
`KeepoutArea`は，立ち入り禁止領域（障害物など）を表す抽象クラスである．
これを派生させて，任意の形の立ち入り禁止領域を表す．
この派生クラスである`CircleKeepoutArea`は円形の立ち入り禁止領域を表していて，ゲーム中では障害物を表現する．
### vehiclemodel.py
`VehicleModel`は，車の内部モデルを表している．NumPyの並列計算機能を駆使して，高速で動作するように作っている．
### vehiclecontrollers.py
`VehicleController`は，制御器，具体的にはCARLAシステムへ受け渡す車操作データを作る抽象クラス．
`G29Controller`は，G29での操作を基に車操作データを作る．
### carlautils
* CARLAシステムとの通信に関するユーティリティメソッド
* CARLAの世界に配置する車アクターと車載カメラアクターを管理し，通信するクラス
### pygamecomponents
再利用可能なGUIコンポーネント．
* `DictViewer`は，キー=値の関係のデータを表示する．`dict_viewer.py`を直接実行すると動作例を見られる．
* `IntervenableScalarView`はステアリング入力の表示に使われている．`intervenable_scalar_view.py`を直接実行すると動作例を見られる．

# Tips
* 次のような引数を与えてCARLAを実行すると，低品質なレンダリングモードを有効にできる．GPUに負荷をかけたくない時におすすめ．
```bash
.\CarlaUnreal.exe -quality-level=Low
```

