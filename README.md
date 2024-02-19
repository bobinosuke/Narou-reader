# Narou-reader
小説家になろうをStyle-Bert-VITS2で読み上げるためのアプリ  
仮想環境をつくってから依存ライブラリをダウンロードしてください。  

## reader.py  
config.jsonで指定した作品を読み込んで読み上げのためのGUIを表示します。  
Style-Bert-VITS2でserver_fastapi.pyを有効にした状態で読み上げを起動すると読み上げが行われます。  

## downloader.py  
起動するとNコードの入力が求められます。入力すると作品全話のテキストがダウンロードされます。

## config.json  
ボイスAPIの設定及びreaderl.pyで読み込む作品のディレクトリが指定できます。  
テキストエディタで編集してください。
