# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :Scheduler.py
# @作者名称 :sxzhang1
# @日期时间 :2025/8/14 09:24
# @文件介绍 :
# @项目编码 :
"""
import queue
import threading
import time

from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import sys
import os

from logger.logger import Logger


class Scheduler:
    def __init__(self):
        self.logger = Logger(title="吾爱破解", is_color=True)


    def run_python_script(self,timeout=120, script_path="吾爱破解.py"):
        self.logger.info(f"🚀 正在运行：{script_path}")
        self.logger.info(f"⏱️  最大运行时间：{timeout} 秒")
        self.logger.info(f"📌 实时输出开始 >>>")
        # 启动子进程
        try:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1
            )
        except Exception as e:
            self.logger.info(f"❌ 启动进程失败：{e}")
            return

        # 使用队列异步读取输出，避免阻塞
        q = queue.Queue()

        def enqueue_output(out, queue):
            for line in iter(out.readline, ''):
                queue.put(('output', line))
            out.close()
            queue.put(('done', None))

        # 开启线程读取 stdout
        thread = threading.Thread(target=enqueue_output, args=(process.stdout, q), daemon=True)
        thread.start()

        # 记录开始时间
        start_time = time.time()
        finished = False
        killed = False

        try:
            while True:
                # 计算剩余时间
                elapsed = time.time() - start_time
                remaining = timeout - elapsed

                if remaining <= 0:
                    self.logger.info(f"\n⏰ 超时！已运行 {timeout} 秒，正在强制终止...")
                    process.terminate()  # 先尝试优雅退出
                    try:
                        # 再等最多 3 秒看是否退出
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.logger.info("💥 进程未响应终止，正在强制杀掉...")
                        process.kill()  # SIGKILL（Windows: TerminateProcess）
                        process.wait()  # 等待彻底结束
                    killed = True
                    break

                # 从队列中非阻塞读取输出
                try:
                    msg_type, value = q.get(timeout=0.1)  # 每 0.1 秒检查一次
                    if msg_type == 'output':
                        line = value.rstrip()
                        self.logger.info(line)
                    elif msg_type == 'done':
                        finished = True
                        break
                except queue.Empty:
                    # 没有输出，继续循环
                    continue

            # 等待主循环结束
            if not killed and not finished:
                # 再检查一次是否自然结束
                rc = process.poll()
                if rc is not None:
                    self.logger.info(f"🔚 脚本自然结束，返回码：{rc}")
                else:
                    self.logger.info(f"\n⏰ 理论超时但未触发，强制终止...")
                    process.kill()
                    process.wait()
            elif killed:
                self.logger.info("❌ 脚本因超时被强制终止")
            else:
                total_time = time.time() - start_time
                self.logger.info(f"📌 实时输出结束 <<<")
                self.logger.info(f"🔚 脚本执行完成，耗时：{total_time:.2f} 秒")
                if process.returncode == 0:
                    self.logger.info("✅ 成功")
                else:
                    self.logger.info(f"❌ 失败，返回码：{process.returncode}")

        except Exception as e:
            self.logger.info(f"💥 意外错误：{type(e).__name__}: {e}")
            if process.poll() is None:
                process.kill()
                self.logger.info("⚠️ 已强制终止子进程")

    def scheduler_task(self):
        self.logger.info("定时任务开始")
        # self.run_python_script()
        scheduler = BlockingScheduler()
        scheduler.add_job(self.run_python_script, trigger='cron', day_of_week='0-6', hour=8, minute=35,
                          misfire_grace_time=1000 * 90)
        scheduler.start()


if __name__ == '__main__':
    Scheduler().scheduler_task()
