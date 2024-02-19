import sys
import os
import time
import re
from urllib import request
from bs4 import BeautifulSoup

dir_base = os.path.dirname(os.path.abspath(__file__))

def get_ncode():
    ncode = input("ダウンロードする作品のN-codeを入力してください: ")
    return ncode

def get_reset_flag(novel_exists):
    if novel_exists:
        reset = input("すでに作品がダウンロードされていますが、すべての部分を再ダウンロードしますか？(Nを入力した場合はダウンロードされていない部分だけダウンロードされます) [y/N]: ")
    else:
        reset = 'y'  
    return reset.strip().lower() == 'y'

def fetch_novel_parts(ncode, reset_flag):
    novel_dir = os.path.normpath(os.path.join(dir_base, f"{ncode}"))
    novel_exists = os.path.exists(novel_dir)
    info_url = f"https://ncode.syosetu.com/novelview/infotop/ncode/{ncode}/"
    try:
        info_res = request.urlopen(info_url)
    except Exception:
        print("N-codeが無効です")
        sys.exit(1)
    soup = BeautifulSoup(info_res, "html.parser")
    pre_info = soup.select_one("#pre_info").text
    match = re.search(r"全([0-9]+)部分", pre_info)
    if match is None:
        print("部分数を特定できませんでした。ページの構造が変更されたか、指定されたN-codeが正しくない可能性があります")
        sys.exit(1)
    if not novel_exists:
        os.makedirs(novel_dir)
    num_parts = int(match.group(1))
    part_pattern = re.compile(rf"{ncode}_([0-9]+).txt")
    existing_parts = {int(part_pattern.search(fn).group(1)) for fn in os.listdir(novel_dir) if part_pattern.search(fn)}
    if reset_flag:
        parts_to_fetch = range(1, num_parts + 1)
    else:
        parts_to_fetch = sorted(set(range(1, num_parts + 1)) - existing_parts)
    for part in parts_to_fetch:
        fetch_and_save_part(ncode, part, novel_dir)
        print(f"part {part} downloaded (rest: {len(parts_to_fetch) - parts_to_fetch.index(part) - 1} parts)")
        time.sleep(1)  # サーバーに過度な負荷をかけないため

def fetch_and_save_part(ncode, part, novel_dir):
    url = f"https://ncode.syosetu.com/{ncode}/{part}/"
    res = request.urlopen(url)
    soup = BeautifulSoup(res, "html.parser")
    content = soup.select_one("#novel_honbun").text + "\n"
    file_path = os.path.join(novel_dir, f"{ncode}_{part}.txt")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

def main():
    ncode = get_ncode()
    novel_dir = os.path.normpath(os.path.join(dir_base, f"{ncode}"))
    novel_exists = os.path.exists(novel_dir)
    reset_flag = get_reset_flag(novel_exists)
    fetch_novel_parts(ncode, reset_flag)

if __name__ == "__main__":
    main()