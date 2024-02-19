import tkinter as tk
import threading
import requests, re, os, tempfile, soundfile as sf, sounddevice as sd
import customtkinter as ctk
import json
import re

class SpeedReadingApp:
    def __init__(self, master):
        self.master = master
        master.title("なろうリーダー")

        # 設定ファイルから設定を読み込む
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.current_file_index = 0
        self.pages = []
        self.current_page = 0
        self.reading_mode = False
        self.file_list = []  # ファイルリストを初期化
        self.episode_options = []  # この行を追加して、episode_options を初期化します。
        self.updating_slider_programmatically = False

        # UIのセットアップ
        self.setup_ui(master)

        # ファイルリストをロード
        self.load_files()

        # コンボボックスのオプションを設定
        self.update_episode_combobox()

    def setup_ui(self, master):
        # ウィンドウのグリッド設定
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)  # テキストエリア用
        master.grid_rowconfigure(1, weight=0)  # スライダー用
        master.grid_rowconfigure(2, weight=0)  # コントロールパネル用

        # テキストエリアの設定
        self.text_area = ctk.CTkTextbox(master, wrap=ctk.WORD, font=("Helvetica", 16))
        self.text_area.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # スライダーの設定
        self.slider = ctk.CTkSlider(master, from_=0, to=100, command=self.slider_moved)
        self.slider.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # コントロールパネルの設定
        self.control_panel = ctk.CTkFrame(master)
        self.control_panel.grid(row=2, column=0, sticky="ew")
        self.control_panel.grid_columnconfigure(0, weight=1)

        # 読み上げボタンの設定
        self.read_button = ctk.CTkButton(self.control_panel, text="読み上げ", command=self.toggle_read, width=50, height=30, font=("Helvetica", 10))
        self.read_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 前へボタンの設定
        self.prev_button = ctk.CTkButton(self.control_panel, text="前のページ", command=self.prev_page, width=50, height=30, font=("Helvetica", 10))
        self.prev_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 次へボタンの設定
        self.next_button = ctk.CTkButton(self.control_panel, text="次のページ", command=self.next_page, width=50, height=30, font=("Helvetica", 10))
        self.next_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # 前のファイルボタンの設定
        self.prev_file_button = ctk.CTkButton(self.control_panel, text="前回", command=self.prev_file, width=50, height=30, font=("Helvetica", 10))
        self.prev_file_button.grid(row=0, column=3, padx=(15, 5), pady=5, sticky="w")

        # 次のファイルボタンの設定
        self.next_file_button = ctk.CTkButton(self.control_panel, text="次回", command=self.next_file, width=50, height=30, font=("Helvetica", 10))
        self.next_file_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # コンボボックスの設定
        self.episode_combobox = ctk.CTkComboBox(self.control_panel, values=self.episode_options, width=100, height=30, command=self.on_episode_selected)
        self.episode_combobox.grid(row=0, column=5, padx=(15, 0), pady=5, sticky="ew")  # 右の余白を0に設定

        # 確定ボタンの設定
        self.confirm_button = ctk.CTkButton(self.control_panel, text="入力した回へ", width=50, height=25, command=self.confirm_selection, font=("Helvetica", 10), fg_color=['#979DA2', '#565B5E'], hover_color=['#6E7174', '#7A848D'],)
        self.confirm_button.grid(row=0, column=6, padx=(0, 5), pady=5, sticky="w")  # 左の余白を0に設定


    def natural_keys(self, text):
        """
        テキスト内の数字を整数として扱い、自然順序ソートのためのキーを生成する
        """
        return [int(c) if c.isdigit() else c for c in re.split('(\d+)', text)]

    def toggle_read(self):
        self.reading_mode = not self.reading_mode
        if self.reading_mode:
            self.read_button.configure(text="停止", fg_color=['#979DA2', '#565B5E'], hover_color=['#6E7174', '#7A848D'])  # 読み上げ中は「停止」と表示し、背景色を赤色に変更
            self.read_current_page()
        else:
            self.read_button.configure(text="読み上げ", fg_color=['#3a7ebf', '#1f538d'], hover_color=['#325882', '#14375e'])  # 読み上げが停止している場合は「読み上げ」と表示し、背景色を緑色に変更

    def update_read_button(self):
        self.read_button.configure(text="読み上げ", fg_color=['#3a7ebf', '#1f538d'], hover_color=['#325882', '#14375e']) 

    def read_current_page(self):
        if 0 <= self.current_page < len(self.pages):
            text = self.pages[self.current_page]
            threading.Thread(target=self.read_text, args=(text,)).start()
        else:
            # 最後のページの読み上げが終了したら、次のファイルがあるかチェック
            if self.current_file_index < len(self.file_list) - 1:
                self.next_file()  # 次のファイルに移動
                #self.reading_mode = True
            else:
                # 最後のファイルの最後のページであれば、読み上げモードをオフにする
                self.reading_mode = False
                self.update_read_button()  # 読み上げボタンの状態を更新

    def read_text(self, text):
        sd.stop()

        # 設定ファイルから読み込んだパラメータを使用
        params = self.config["voice_api"]
        params['text'] = text  # テキスト内容のみ動的に設定

        API_URL = "http://127.0.0.1:5000/voice"
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_file_name = tmp_file.name
            
            data, fs = sf.read(tmp_file_name)
            sd.play(data, fs)
            sd.wait()  # 音声再生が完了するまで待機
            os.remove(tmp_file_name)  # 一時ファイルを削除
            
            # 音声再生が完了した後の処理
            if self.reading_mode:
                if self.current_page < len(self.pages) - 1:
                    self.current_page += 1
                    self.display_current_page()  # 現在のページを表示更新
                    self.read_current_page()  # 次のページの読み上げを開始
                else:
                    # 最後のページの場合の処理
                    if self.current_file_index < len(self.file_list) - 1:
                        self.current_file_index += 1
                        self.display_current_file()  # 新しいファイルを表示
                        self.read_current_page()  # 新しいファイルの最初のページの読み上げを開始
                    else:
                        self.reading_mode = False  # 最後のファイルで読み上げが終了した場合
                        self.update_read_button()  # 読み上げボタンの状態を更新
        else:
            print(f"Failed to get audio data: {response.status_code}")

    def load_files(self):
        novel_dir = self.config["ncode_dir"]
        # 自然順序ソートを使用してファイルリストをソート
        self.file_list = sorted(os.listdir(novel_dir), key=self.natural_keys)
        # ファイル名が指定のパターンに一致するもののみを選択
        self.file_list = [file for file in self.file_list if re.match(r'.*?_\d+\.txt', file)]
        self.display_current_file()

    def confirm_selection(self):
        # コンボボックスの現在の選択を取得して処理を実行
        self.reading_mode = False  # 読み上げモードをオフにする
        sd.stop()  # 読み上げを停止する
        self.update_read_button()
        choice = self.episode_combobox.get()
        self.on_episode_selected(choice)

    def update_episode_combobox(self):
        # コンボボックスのオプションを更新
        self.episode_options = [re.search(r'_(\d+)\.txt', file).group(1) for file in self.file_list]

        # 以前のコンボボックスを削除する
        if hasattr(self, 'episode_combobox'):
            self.episode_combobox.destroy()

        # 新しいコンボボックスを作成する
        self.episode_combobox = ctk.CTkComboBox(self.control_panel, values=self.episode_options, width=100, height=25, command=self.on_episode_selected)
        self.episode_combobox.grid(row=0, column=5, padx=10, pady=5, sticky="ew")

        # 現在選択されているファイルに基づいてコンボボックスの値を設定
        if self.file_list:
            selected_episode = re.search(r'_(\d+)\.txt', self.file_list[self.current_file_index]).group(1)
            self.episode_combobox.set(selected_episode)

    def on_episode_selected(self, choice):
        self.reading_mode = False  # 読み上げモードをオフにする
        sd.stop()  # 読み上げを停止する
        self.update_read_button()
        # 選択された話数（choice）に基づいてファイルを検索
        selected_episode = choice  # 選択された話数
        selected_file = None

        # ファイルリストから選択された話数に対応するファイルを検索
        for file in self.file_list:
            if re.search(f'_{selected_episode}\.txt', file):
                selected_file = file
                break

        if selected_file is not None:
            # 対応するファイルが見つかった場合、そのファイルを表示する処理
            self.current_file_index = self.file_list.index(selected_file)
            self.display_current_file()
        else:
            # 対応するファイルが見つからなかった場合の処理（エラーメッセージの表示など）
            print(f"選択された話数{selected_episode}に対応するファイルが見つかりません。")

    def display_current_file(self):
        if 0 <= self.current_file_index < len(self.file_list):
            self.current_page = 0  # 現在のページをリセット
            novel_dir = self.config["ncode_dir"]
            file_path = os.path.join(novel_dir, self.file_list[self.current_file_index])
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            self.display_text(text)
            self.split_text_into_pages(text)
            self.display_current_page()
            self.update_slider()
            #self.reading_mode = True 不具合があればTrue

            # コンボボックスのオプションを更新
            self.update_episode_combobox()
            # コンボボックスの選択値を設定
            self.set_episode_combobox_value()

    def convert(self, text):
        text = re.split(r'\-{5,}', text)[2]
        text = re.split(r'底本：', text)[0]
        text = re.sub(r'《.+?》|［＃.+?］|｜', '', text)  # ルビ、注釈、傍点の開始記号を削除
        return text.strip()

    def split_text_into_pages(self, text):
        pages = re.split(r'(?<=。)|(?<=\n)|(?<=」)|(?<=』)|(?<=\))', text)
        pages = [page.strip() for page in pages if page.strip()]
        self.pages = self.adjust_pages(pages)

    def adjust_pages(self, pages):
        adjusted_pages, temp_page = [], ""
        for page in pages:
            if temp_page:
                page = temp_page + page
                temp_page = ""
            if any(x in page and y not in page for x, y in [('「', '」'), ('『', '』'), ('（', '）')]):
                temp_page = page
            else:
                adjusted_pages.append(page)
        if temp_page:
            adjusted_pages.append(temp_page)
        return [page for page in adjusted_pages if re.sub(r'[^\w\s]', '', page).strip()]

    def display_text(self, text):
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert(tk.END, text)

    def display_current_page(self):
        if 0 <= self.current_page < len(self.pages):
            self.display_text(self.pages[self.current_page])
            self.slider.set(self.current_page + 1)

    def slider_moved(self, event):
        new_page = int(self.slider.get()) - 1
        page_diff = abs(new_page - self.current_page)  # 現在のページと新しいページの差を計算

        if page_diff >= 2:  # スライダーが2ページ以上動かされた場合
            self.reading_mode = False  # 読み上げモードをオフにする
            sd.stop()  # 読み上げを停止する
            self.update_read_button()  # 読み上げボタンの状態を更新

        self.current_page = new_page
        self.display_current_page()

        if not self.updating_slider_programmatically:  # プログラムによる更新でない場合のみ
            self.reading_mode = False  # 読み上げモードを再度オフにする（念のため）
            self.update_read_button()  # ここでもボタンの状態を更新
        self.updating_slider_programmatically = False  # フラグをリセット

    def update_slider(self):
        # スライダーの最小値を1に設定（ページ番号は1から始まる）
        from_value = 1
        # スライダーの最大値をページの総数に設定
        to_value = len(self.pages)
        # スライダーの設定を更新
        self.slider.configure(from_=from_value, to=to_value)
        # スライダーの現在の値を現在のページに設定
        self.slider.set(self.current_page + 1)

    def next_page(self):
        self.reading_mode = False  # 読み上げモードをオフにする
        sd.stop()  # 読み上げを停止する
        self.update_read_button()
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.display_current_page()

    def prev_page(self):
        self.reading_mode = False  # 読み上げモードをオフにする
        sd.stop()  # 読み上げを停止する
        self.update_read_button()
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page()

    def next_file(self):
        self.reading_mode = False  # 読み上げモードをオフにする
        sd.stop()  # 読み上げを停止する
        self.update_read_button()
        if self.current_file_index < len(self.file_list) - 1:
            self.current_file_index += 1
            self.display_current_file()

    def prev_file(self):
        self.reading_mode = False  # 読み上げモードをオフにする
        sd.stop()  # 読み上げを停止する
        self.update_read_button()
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.display_current_file()

    def set_episode_combobox_value(self):
        # 現在選択されているファイルに基づいてコンボボックスの値を設定
        if self.file_list:
            selected_episode = re.search(r'_(\d+)\.txt', self.file_list[self.current_file_index]).group(1)
            self.episode_combobox.set(selected_episode)

if __name__ == "__main__":
    root = ctk.CTk()
    root.minsize(600, 400)
    app = SpeedReadingApp(root)
    root.mainloop()