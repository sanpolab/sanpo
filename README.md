# 打鐘 -JAN- iPhoneアプリ（このブランチだけで完結）

- ゲーム本体は公開サイト sanpolab/jan をそのまま中に入れて、Capacitor で iPhone アプリにする
- Appleの鍵は、このリポジトリ（sanpo）に登録済みのものを使う

手順（Actions から手動で動かす）:
1. `JAN 1 bundle` … アプリのID（io.github.sanpolab.jan）を Apple に登録
2. App Store Connect でアプリを新規作成（このIDを選ぶ）※ここだけ手作業
3. `JAN 2 build` … 組み立てて App Store Connect に送る
4. `JAN 3 store` … 説明文・スクショ・年齢制限などを入力
5. `JAN 4 submit` … 審査に提出

動かし方：`run/bundle.txt` `run/build.txt` `run/store.txt` `run/submit.txt` のどれかを書きかえてこのブランチに送ると、その作業が動く。
