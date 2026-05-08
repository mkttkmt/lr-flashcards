# LR-Flashcards

Language Reactor からエクスポートした単語のフラッシュカードアプリ。

🌐 **公開URL**: https://mkttkmt.github.io/lr-flashcards/

## 仕組み

1. LR から JSON エクスポート
2. `data/items.json` として上書きアップロード
3. GitHub Actions が自動で `index.html` を再生成
4. GitHub Pages が公開URLを更新
5. iPhone のホーム画面アプリで最新版が見られる

## 更新方法

1. Language Reactor を開く
2. 「保存したアイテム」→「エクスポート」→「JSON」を選択
3. ダウンロードした JSON ファイルを **`items.json` にリネーム**
4. このリポジトリの `data/items.json` を Web画面から上書きアップロード
   - GitHub上で `data/items.json` を開く → 鉛筆アイコン → ファイルを置き換える
5. コミット → 1〜2分待つ → アプリ再読込

## ファイル構成

```
.
├── data/
│   └── items.json          # LRエクスポートJSON（手動更新）
├── scripts/
│   ├── build.py            # ビルドスクリプト
│   └── template.html       # HTMLテンプレート
├── .github/workflows/
│   └── build.yml           # GitHub Actions ワークフロー
├── index.html              # 自動生成される成果物
├── apple-touch-icon.png    # ホーム画面アイコン
└── README.md
```

## 仕様

- LR の `freqRank` 上位 100 語を抽出
- 重み付きランダム抽選（苦手な単語ほど頻出）
- 「覚えた」5 回で習得判定
- 評価データは localStorage に永続保存
- JSON更新時、新JSONに無い単語の履歴は自動削除
- 機械翻訳（占星術系）の英語例文は非表示

## ローカルでビルド

```bash
python scripts/build.py
```
