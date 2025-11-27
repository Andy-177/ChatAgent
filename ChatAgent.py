import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, StringVar
from pydantic import BaseModel
import requests
import threading
import subprocess
import re
import platform

# 定义配置模型
class Config(BaseModel):
    api_url: str = "https://api.example.com/v1/chat/completions"
    api_key: str = "your_api_key_here"
    model: str = "default_model"
    user_name: str = "用户"
    ai_name: str = "AI"
    prompt_file: str = "无"  # 默认值为“无”

    def save_to_file(self, file_path="config.json"):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.dict(), f, indent=4)

    @classmethod
    def load_from_file(cls, file_path="config.json"):
        if not os.path.exists(file_path):
            return cls()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except json.JSONDecodeError:
            return cls()

# 定义聊天工具类
class AIChatTool:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Chat Tool")
        self.config = Config.load_from_file()
        self.prompt_files = self.get_prompt_files()
        self.selected_prompt = StringVar()
        self.selected_prompt.set(self.config.prompt_file)  # 从配置中加载提示词文件名称
        self.create_widgets()

    def get_prompt_files(self):
        """获取根目录下的所有 .txt 文件"""
        files = [f for f in os.listdir() if f.endswith('.txt')]
        print(f"Found prompt files: {files}")  # 调试输出
        return ["无"] + files  # 添加“无”选项

    def refresh_prompt_menu(self):
        """刷新提示词菜单"""
        self.prompt_files = self.get_prompt_files()
        self.prompt_menu["values"] = self.prompt_files
        if self.config.prompt_file in self.prompt_files:
            self.selected_prompt.set(self.config.prompt_file)  # 设置为配置中的提示词文件
        else:
            self.selected_prompt.set(self.prompt_files[0])  # 如果配置中的文件不存在，则设置为默认值

    def create_widgets(self):
        # 配置框
        config_frame = ttk.LabelFrame(self.root, text="配置", padding=5)
        config_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(config_frame, text="API URL:").grid(row=0, column=0, sticky="w")
        self.api_url_entry = ttk.Entry(config_frame, width=50)
        self.api_url_entry.grid(row=0, column=1, padx=5, pady=2)
        self.api_url_entry.insert(0, self.config.api_url)

        ttk.Label(config_frame, text="API Key:").grid(row=1, column=0, sticky="w")
        self.api_key_entry = ttk.Entry(config_frame, width=50)
        self.api_key_entry.grid(row=1, column=1, padx=5, pady=2)
        self.api_key_entry.insert(0, self.config.api_key)

        ttk.Label(config_frame, text="模型:").grid(row=2, column=0, sticky="w")
        self.model_entry = ttk.Entry(config_frame, width=50)
        self.model_entry.grid(row=2, column=1, padx=5, pady=2)
        self.model_entry.insert(0, self.config.model)

        ttk.Label(config_frame, text="用户名:").grid(row=3, column=0, sticky="w")
        self.user_name_entry = ttk.Entry(config_frame, width=50)
        self.user_name_entry.grid(row=3, column=1, padx=5, pady=2)
        self.user_name_entry.insert(0, self.config.user_name)

        ttk.Label(config_frame, text="AI 名字:").grid(row=4, column=0, sticky="w")
        self.ai_name_entry = ttk.Entry(config_frame, width=50)
        self.ai_name_entry.grid(row=4, column=1, padx=5, pady=2)
        self.ai_name_entry.insert(0, self.config.ai_name)

        ttk.Label(config_frame, text="提示词文件:").grid(row=5, column=0, sticky="w")
        self.prompt_menu = ttk.Combobox(config_frame, textvariable=self.selected_prompt, values=self.prompt_files)
        self.prompt_menu.grid(row=5, column=1, padx=5, pady=2, sticky="w")
        self.selected_prompt.set(self.config.prompt_file)  # 设置为配置中的提示词文件

        save_config_button = ttk.Button(config_frame, text="保存配置", command=self.save_config)
        save_config_button.grid(row=6, column=1, pady=5, sticky="e")

        # 聊天框
        chat_frame = ttk.LabelFrame(self.root, text="聊天", padding=5)
        chat_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, width=60, height=20)
        self.chat_display.pack(padx=5, pady=5, fill="both", expand=True)

        # 输入框
        input_frame = ttk.Frame(self.root)
        input_frame.pack(padx=10, pady=5, fill="x")

        self.user_input = ttk.Entry(input_frame)
        self.user_input.pack(side="left", fill="x", expand=True, padx=(0, 5))

        send_button = ttk.Button(input_frame, text="发送", command=self.send_message)
        send_button.pack(side="right")

    def save_config(self):
        self.config.api_url = self.api_url_entry.get()
        self.config.api_key = self.api_key_entry.get()
        self.config.model = self.model_entry.get()
        self.config.user_name = self.user_name_entry.get()
        self.config.ai_name = self.ai_name_entry.get()
        self.config.prompt_file = self.selected_prompt.get()  # 保存提示词文件名称
        self.config.save_to_file()
        messagebox.showinfo("提示", "配置已保存！")

    def send_message(self):
        user_message = self.user_input.get()
        if not user_message:
            return

        self.chat_display.insert(tk.END, f"{self.config.user_name}: {user_message}\n")
        self.user_input.delete(0, tk.END)

        # 使用多线程发送消息，避免 UI 卡顿
        threading.Thread(
            target=self.call_api,
            args=(user_message,),
            daemon=True
        ).start()

    def call_api(self, user_message):
        try:
            # 构建系统提示词
            system_content = f"你是一个名为{self.config.ai_name}的AI助手，正在与用户{self.config.user_name}对话。"
            system_content += f"\n当前系统类型是：{platform.system()}"
            system_content += "\n你可以使用以下命令格式："
            system_content += "\n~!run:[cmd:<命令>]!~ 执行命令行命令"
            system_content += "\n~!run:[shell:<命令>]!~ 执行 Shell 命令"
            system_content += "\n~!run:[ps:<命令>]!~ 执行 PowerShell 命令"
            system_content += "\n~!get:[systype]!~ 获取当前系统类型"

            # 如果选择了提示词文件，则读取文件内容并追加到系统提示词
            selected_prompt = self.selected_prompt.get()
            if selected_prompt != "无":
                with open(selected_prompt, "r", encoding="utf-8") as f:
                    prompt_content = f.read()
                system_content += f"\n{prompt_content}"

            # 构建消息列表
            messages = [
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]

            response = requests.post(
                self.config.api_url,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={"model": self.config.model, "messages": messages}
            )

            if response.status_code == 200:
                ai_response = response.json().get("choices", [{}])[0].get("message", {}).get("content", "未获取到回复")
                self.handle_ai_response(ai_response)
            else:
                self.chat_display.insert(tk.END, f"{self.config.ai_name}: 错误: {response.text}\n")
        except Exception as e:
            self.chat_display.insert(tk.END, f"{self.config.ai_name}: 请求失败: {str(e)}\n")

    def handle_ai_response(self, ai_response):
        # 使用正则表达式匹配命令
        pattern = r"~!run:\[(cmd|shell|ps):(.+?)\]!~"
        matches = re.findall(pattern, ai_response)

        if matches:
            for match in matches:
                command_type = match[0]
                command = match[1].strip()
                threading.Thread(target=self.run_command, args=(command_type, command), daemon=True).start()
        else:
            self.chat_display.insert(tk.END, f"{self.config.ai_name}: {ai_response}\n")

    def run_command(self, command_type, command):
        try:
            if command_type == "cmd":
                result = subprocess.run(command, shell=True, text=True, capture_output=True)
            elif command_type == "shell":
                result = subprocess.run(command, shell=True, text=True, capture_output=True)
            elif command_type == "ps":
                result = subprocess.run(["powershell", "-Command", command], text=True, capture_output=True)
            else:
                self.chat_display.insert(tk.END, f"{self.config.ai_name}: 未知命令类型\n")
                return

            output = result.stdout.strip()
            error = result.stderr.strip()

            if not output and not error:
                # 如果没有返回内容，发送“没有返回内容”给 AI
                self.call_api("没有返回内容")
            else:
                # 如果有返回内容，将返回内容发送给 AI
                response_content = f"命令输出: {output}\n命令错误: {error}\n" if error else f"命令输出: {output}\n"
                self.call_api(response_content)
        except Exception as e:
            self.chat_display.insert(tk.END, f"命令执行失败: {str(e)}\n")

# 运行程序
if __name__ == "__main__":
    root = tk.Tk()
    app = AIChatTool(root)
    root.mainloop()