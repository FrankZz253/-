import re
import requests
import traceback
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
from io import BytesIO
import webbrowser
import urllib.parse

stop_crawl = False
progress_bar = None  # 全局进度条变量

SOURCES = {"百度图片": "baidu", "360 图片": "360"}

# ---------- 百度 ----------
def download_baidu(html, keyword, start_num, save_path, suffix,
                   progress_var, total_count, current_count, max_download, progress_label):  # 修复：添加参数
    global stop_crawl
    headers = {'user-agent': 'Mozilla/5.0'}
    pic_urls = re.findall('"objURL":"(.*?)",', html, re.S)
    i = start_num
    ok_cnt = 0
    subroot = os.path.join(save_path, keyword)
    txtpath = os.path.join(subroot, 'download_detail.txt')
    os.makedirs(subroot, exist_ok=True)

    for url in pic_urls:
        if ok_cnt >= max_download or stop_crawl:  # 修复：使用 max_download
            break
        path = os.path.join(subroot, f'{i}.{suffix}')
        try:
            for _ in range(3):
                if not os.path.exists(path):
                    pic = requests.get(url, headers=headers, timeout=10)
                    img = Image.open(BytesIO(pic.content))
                    img.save(path)
                    with open(txtpath, 'a', encoding='utf-8') as f:
                        f.write(f'图片 {i}, URL: {url}\n')
                    ok_cnt += 1
                    # 修复：计算整体进度
                    progress = (current_count + ok_cnt) / total_count * 100
                    progress_var.set(progress)
                    progress_label.config(text=f"{progress:.2f}%")
                    progress_bar.update()
                    i += 1
                    break
        except Exception as e:
            print(f'百度图片下载失败: {e}')
    return ok_cnt

# ---------- 360 ----------
def download_360(keyword, start_num, save_path, suffix,
                 progress_var, total_count, current_count, max_download, progress_label, frequency):  # 修复：添加参数
    global stop_crawl
    headers = {'user-agent': 'Mozilla/5.0'}
    subroot = os.path.join(save_path, keyword)
    txtpath = os.path.join(subroot, 'download_detail.txt')
    os.makedirs(subroot, exist_ok=True)

    page = 1
    per = 30
    i = start_num
    ok_cnt = 0

    while ok_cnt < max_download and not stop_crawl:  # 修复：使用 max_download
        api = f'https://image.so.com/j?q={urllib.parse.quote(keyword)}&src=srp&pn={page}&sn={(page-1)*per}&kn=50'
        try:
            resp = requests.get(api, headers=headers, timeout=10).json()
            if 'list' not in resp or not resp['list']:
                break
            for item in resp['list']:
                if ok_cnt >= max_download or stop_crawl:  # 修复：使用 max_download
                    break
                img_url = item.get('img')
                if not img_url:
                    continue
                path = os.path.join(subroot, f'{i}.{suffix}')
                try:
                    for _ in range(3):
                        if not os.path.exists(path):
                            pic = requests.get(img_url, headers=headers, timeout=10)
                            img = Image.open(BytesIO(pic.content))
                            img.save(path)
                            with open(txtpath, 'a', encoding='utf-8') as f:
                                f.write(f'图片 {i}, URL: {img_url}\n')
                            ok_cnt += 1
                            # 修复：计算整体进度
                            progress = (current_count + ok_cnt) / total_count * 100
                            progress_var.set(progress)
                            progress_label.config(text=f"{progress:.2f}%")
                            progress_bar.update()
                            i += 1
                            break
                except Exception as e:
                    print(f'360 图片下载失败: {e}')
            page += 1
            time.sleep(frequency)  # 修复：使用用户设置的频率
        except Exception as e:
            print(f'360 API 请求失败: {e}')
            break
    return ok_cnt

# ---------- 启动下载 ----------
def start_download():
    global stop_crawl
    stop_crawl = False
    keyword = entry_keyword.get().strip()
    save_path = entry_save_path.get().strip()
    num_images = int(entry_images.get().strip())
    frequency = int(entry_frequency.get().strip())
    suffix = combo_suffix.get().strip()
    start_num = int(entry_start_num.get().strip())
    source_name = combo_source.get().strip()

    if not keyword or not save_path or not suffix or source_name not in SOURCES:
        messagebox.showerror("输入错误", "请填写所有字段并选择正确图库")
        return

    progress_var.set(0)
    progress_label.config(text="0%")
    progress_bar.update()

    source_code = SOURCES[source_name]
    success_count = 0

    if source_code == "baidu":
        page_id = 0
        while success_count < num_images and not stop_crawl:
            url = f'http://image.baidu.com/search/flip?tn=baiduimage&ie=utf-8&word={keyword}&pn={page_id}'
            page_id += 20
            html = requests.get(url, headers={'user-agent': 'Mozilla/5.0'}, timeout=10).text
            # 修复：传递正确的参数
            downloaded = download_baidu(
                html, keyword, success_count + start_num, 
                save_path, suffix, progress_var, 
                num_images, success_count,  # total_count, current_count
                num_images - success_count,  # max_download
                progress_label
            )
            success_count += downloaded
            time.sleep(frequency)

    elif source_code == "360":
        # 修复：传递正确的参数
        success_count += download_360(
            keyword, start_num, save_path, suffix,
            progress_var, num_images, 0,  # total_count, current_count
            num_images,  # max_download
            progress_label, frequency
        )

    messagebox.showinfo("下载完成", f"关键词 '{keyword}' 的图片已下载完成（来源：{source_name}）")

# ... 其余代码保持不变 ...
def stop_download():
    global stop_crawl
    stop_crawl = True
    messagebox.showinfo("停止下载", "图片下载已手动停止")

def browse_save_path():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry_save_path.delete(0, tk.END)
        entry_save_path.insert(0, folder_selected)

def open_save_path():
    path = entry_save_path.get().strip()
    if os.path.exists(path):
        webbrowser.open(path)
    else:
        messagebox.showerror("路径错误", "保存路径不存在")

# ---------- GUI ----------
root = tk.Tk()
root.title("图片下载器")
root.geometry("550x330")

style = ttk.Style()
style.configure("TButton", font=("Helvetica", 10))
style.configure("TLabel", font=("Helvetica", 10))
style.configure("TEntry", font=("Helvetica", 10))
style.configure("TCombobox", font=("Helvetica", 10))

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
frame.columnconfigure(1, weight=1)

# row 0
ttk.Label(frame, text="图库来源:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
combo_source = ttk.Combobox(frame, values=list(SOURCES.keys()), state="readonly")
combo_source.set("百度图片")
combo_source.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

# row 1
ttk.Label(frame, text="关键词:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
entry_keyword = ttk.Entry(frame, width=30)
entry_keyword.insert(0, "猫")
entry_keyword.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

# row 2
ttk.Label(frame, text="保存路径:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
entry_save_path = ttk.Entry(frame, width=30)
entry_save_path.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
ttk.Button(frame, text="浏览", command=browse_save_path).grid(row=2, column=2, padx=5, pady=5)
ttk.Button(frame, text="打开", command=open_save_path).grid(row=2, column=3, padx=5, pady=5)

# row 3
ttk.Label(frame, text="爬取图片数量:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
entry_images = ttk.Entry(frame, width=30)
entry_images.insert(0, "20")
entry_images.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

# row 4
ttk.Label(frame, text="爬取频率 (秒):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
entry_frequency = ttk.Entry(frame, width=30)
entry_frequency.insert(0, "1")
entry_frequency.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

# row 5
ttk.Label(frame, text="图片格式:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
combo_suffix = ttk.Combobox(frame, values=["jpg", "png", "jpeg"], state="readonly")
combo_suffix.set("jpg")
combo_suffix.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

# row 6
ttk.Label(frame, text="起始编号:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
entry_start_num = ttk.Entry(frame, width=30)
entry_start_num.insert(0, "1")
entry_start_num.grid(row=6, column=1, padx=5, pady=5, sticky="ew")

# row 7
ttk.Button(frame, text="开始下载", command=start_download).grid(row=7, column=0, padx=5, pady=5, sticky="ew")
ttk.Button(frame, text="停止下载", command=stop_download).grid(row=7, column=1, padx=5, pady=5, sticky="ew")

# row 8
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
progress_bar.grid(row=8, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
progress_label = ttk.Label(frame, text="0%")
progress_label.grid(row=8, column=2, padx=5, pady=5, sticky="e")

root.mainloop()