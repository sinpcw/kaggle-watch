# kaggle-watch
kaggle apiを利用してNotebook Submitの際に送信情報を監視し, 実行時間等を取得するためのツール.  
SlackやDiscordのWebhook機能を利用してLBや実行時間等を含めてメッセージを送信する.  
  
<img src="resource/example.png" width="600px" />  

[コンペ](https://www.kaggle.com/competitions/uw-madison-gi-tract-image-segmentation)での活用例.  
9時間(540分)の制限に対して, あと程度処理が可能かなどを検討する際に有用であった.  

## kaggle API の設定

Python で kaggle API を利用できるようにする.  
すでに利用できている人には不要な項目なのでスキップ.  
いままで利用していなければ https://www.kaggle.com/settings/account から Create New Token を実行.  
```bash
# Windows:
C:\\Users\\<username>\\.kaggle  
# Linux:
/home/<username>/.kaggle  
```
上記パスに kaggle.json を配置する.  
  
```bash
kaggle competitions submissions -c xxxx
# (xxxx部分はコンペティションを指定する)
```
に対して fileName, date などの列が表示されれば準備できている.  
上記の xxxx 部分は main.py にも使用するのでコピーしておく.  

## Discord の設定

<font color="#ff0000">**注意**</font>  
事前にkaggle APIを実行可能および認証情報を取得していることが必要になる.  

本コードではDiscordを想定している

### 1. 監視ログを送信したいDiscrodサーバー/チャンネルでWebhookを作成  
<img src="resource/op1.png" width="600px" />  
  
### 2. Webhook作成時のURLを取得  
<img src="resource/op2.png" width="600px" />  

<img src="resource/op3.png" width="600px" />  
  
### 3. コード設定
main.py のコードを編集してWebhook送信先URLおよびコンペID、Max/Minなどを編集する.  
<img src="resource/op4.png" width="600px" />
  
### 4. 実行  
実行することで監視を開始.  
```bash
python main.py
```
report/xxxx.csv というファイルを生成する (ログファイル).  
Ctrl+Cで停止できる. quit というファイルを作っても停止可能.  
    
<font color="#ff0000">**注意**</font>  
起動している間にネットワーク疎通ができず、かつその間に submit が終了した場合は  
submit時間が正しく計測できないので注意すること.  

## メモ
Slackのテストをしていないので json などの指定ミスはあるかもしれない.  
