#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Luneshost 自动登录脚本 - 使用 Botasaurus 绕过 Cloudflare
支持 Cookie 复用以绕过 reCAPTCHA
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from botasaurus.browser import browser, Driver
import requests

# 加载环境变量
load_dotenv()


def send_telegram_message(bot_token, chat_id, message):
    """发送 Telegram 通知"""
    if not bot_token or not chat_id:
        print("⚠️  Telegram 配置未设置，跳过通知")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Telegram 通知已发送")
    except Exception as e:
        print(f"⚠️  Telegram 通知失败: {e}")


@browser(
    block_images=False,
    headless=False,  # 始终使用有界面模式（CI 使用 Xvfb 虚拟显示）
    reuse_driver=False,
    add_arguments=[
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
        '--window-size=1920,1080'
    ]
)
def login_task(driver: Driver, data):
    """
    登录任务主函数 - 支持 Cookie 复用
    """
    website_url = os.getenv('WEBSITE_URL')
    username = os.getenv('LOGIN_USERNAME')
    password = os.getenv('LOGIN_PASSWORD')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    saved_cookies = os.getenv('SAVED_COOKIES')  # Cookie 复用

    # 验证必需的环境变量
    if not all([website_url, username, password]):
        error_msg = "❌ 错误：缺少必需的环境变量（WEBSITE_URL, LOGIN_USERNAME, LOGIN_PASSWORD）"
        print(error_msg)
        send_telegram_message(
            telegram_token, telegram_chat_id, f"*登录失败*\\n{error_msg}")
        return {"success": False, "error": "Missing environment variables"}

    # ========== Cookie 复用登录 ==========
    if saved_cookies:
        try:
            print("🍪 检测到已保存的 Cookie，尝试免登录...")

            # 先访问网站
            driver.get(website_url)
            driver.sleep(2)

            # 加载 Cookie
            cookies = json.loads(saved_cookies)
            print(f"📦 正在加载 {len(cookies)} 个 Cookie...")

            cookie_loaded = 0
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                    cookie_loaded += 1
                except:
                    pass

            print(f"✅ 成功加载 {cookie_loaded} 个 Cookie")
            print("🔄 刷新页面...")
            driver.refresh()
            driver.sleep(5)

            # 检查是否已登录
            current_url = driver.current_url
            current_title = driver.title

            print(f"📄 当前页面: {current_title}")
            print(f"🔗 当前 URL: {current_url}")

            if '/login' not in current_url.lower():
                print("🎉 使用 Cookie 免登录成功！")

                # 尝试访问服务器控制台
                try:
                    print("🖱️  查找服务器卡片...")
                    server_card = driver.select("a.server-card", wait=10)

                    if server_card:
                        server_title_elem = driver.select(
                            ".server-title", wait=2)
                        server_title = server_title_elem.text if server_title_elem else "未知"

                        print(f"✅ 找到服务器: {server_title}")
                        server_card.click()
                        driver.sleep(3)

                        final_url = driver.current_url
                        final_title = driver.title

                        print(f"✅ 已访问服务器控制台")
                        print(f"📄 服务器页面: {final_title}")
                        print(f"🔗 服务器 URL: {final_url}")

                        success_msg = f"""*✅ Cookie 免登录成功！*

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 当前页面: {final_url}
📄 标题: {final_title}
✨ 已访问服务器控制台，账户保持活跃
🍪 使用 Cookie 复用，无需登录验证
"""
                        send_telegram_message(
                            telegram_token, telegram_chat_id, success_msg)

                        return {
                            "success": True,
                            "url": final_url,
                            "title": final_title,
                            "method": "cookie"
                        }
                except Exception as e:
                    print(f"⚠️  访问服务器时出错: {e}")

                # 即使没访问到服务器，登录也成功了
                success_msg = f"""*✅ Cookie 免登录成功！*

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 当前页面: {current_url}
📄 标题: {current_title}
🍪 使用 Cookie 复用，无需登录验证
"""
                send_telegram_message(
                    telegram_token, telegram_chat_id, success_msg)

                return {
                    "success": True,
                    "url": current_url,
                    "title": current_title,
                    "method": "cookie"
                }
            else:
                print("⚠️  Cookie 已失效，将进行正常登录...")
                print("💡 提示：请运行 `python export_cookies.py` 更新 Cookie")
        except Exception as e:
            print(f"⚠️  Cookie 登录失败: {e}")
            print("🔄 将进行正常登录...")
    # ========== Cookie 复用登录结束 ==========

    try:
        print("🌐 开始登录流程...")
        print(f"📍 目标网站: {website_url}")

        # 步骤 1: 先访问 Google（建立真实的 Referer）
        print("🔍 通过 Google 搜索建立 Referer...")
        driver.google_get(
            "https://www.google.com/search?q=betadash+lunes+host")
        driver.sleep(2)  # 短暂停留

        # 步骤 2: 访问登录页面并绕过 Cloudflare
        print("🚀 访问登录页面并绕过 Cloudflare...")
        driver.google_get(website_url, bypass_cloudflare=True)

        # 等待页面完全加载
        print("⏳ 等待页面加载...")
        driver.sleep(3)

        # 检查是否成功加载登录页面
        current_url = driver.current_url
        page_title = driver.title
        print(f"📄 当前页面: {page_title}")
        print(f"🔗 当前 URL: {current_url}")

        # 步骤 3: 查找并填写登录表单
        print("📝 填写登录信息...")

        # 输入邮箱
        email_input = driver.select("#email", wait=10)
        if not email_input:
            raise Exception("未找到邮箱输入框")
        email_input.type(username)

        # 输入密码
        password_input = driver.select("#password", wait=5)
        if not password_input:
            raise Exception("未找到密码输入框")
        password_input.type(password)

        print("✅ 登录信息已填写")

        # 短暂停顿（模拟人类行为）
        driver.sleep(1)

        # 步骤 4: 提交表单
        print("🔄 提交登录表单...")
        submit_button = driver.select('button[type="submit"]', wait=5)
        if not submit_button:
            raise Exception("未找到提交按钮")

        submit_button.click()

        # 等待页面跳转（增加等待时间给 reCAPTCHA）
        print("⏳ 等待登录结果（包括 reCAPTCHA 验证）...")
        driver.sleep(15)  # 给 reCAPTCHA 更多时间

        # 步骤 5: 验证登录状态
        final_url = driver.current_url
        final_title = driver.title

        print(f"📄 登录后页面: {final_title}")
        print(f"🔗 登录后 URL: {final_url}")

        # 改进的判断逻辑：检查是否离开登录页面或者 URL 改变了
        login_success = False

        # 方法1: URL 不包含 /login
        if '/login' not in final_url.lower():
            login_success = True
            print("✅ 检测到 URL 已改变，登录成功")
        # 方法2: 标题不包含 Login
        elif 'login' not in final_title.lower():
            login_success = True
            print("✅ 检测到标题已改变，登录成功")
        # 方法3: 能找到服务器卡片（说明在主页）
        else:
            print("🔍 检查是否能找到服务器卡片...")
            test_card = driver.select("a.server-card", wait=3)
            if test_card:
                login_success = True
                print("✅ 找到服务器卡片，登录成功")

        # 判断登录是否成功
        if login_success:
            print("🎉 登录成功！")

            # === 点击服务器卡片以保持账户活跃 ===
            try:
                print("🖱️  查找服务器卡片...")
                # 查找 server-card 链接
                server_card = driver.select("a.server-card", wait=10)

                if server_card:
                    # 获取服务器信息
                    server_title_elem = driver.select(".server-title", wait=2)
                    server_title = server_title_elem.text if server_title_elem else "未知"

                    print(f"✅ 找到服务器: {server_title}")
                    print("🔗 点击服务器卡片...")

                    server_card.click()

                    # 等待页面跳转
                    driver.sleep(3)

                    # 获取跳转后的页面信息
                    server_url = driver.current_url
                    server_page_title = driver.title

                    print(f"✅ 已访问服务器控制台")
                    print(f"📄 服务器页面: {server_page_title}")
                    print(f"🔗 服务器 URL: {server_url}")

                    # 更新最终 URL（用于 Telegram 通知）
                    final_url = server_url
                    final_title = server_page_title
                else:
                    print("⚠️  未找到服务器卡片，可能页面结构已变化")

            except Exception as e:
                print(f"⚠️  点击服务器卡片时出错: {e}")
                print("💡 继续执行，登录已成功")

            # 发送成功通知
            success_msg = f"""*✅ 登录成功！*

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 当前页面: {final_url}
📄 标题: {final_title}
✨ 已访问服务器控制台，账户保持活跃
"""
            send_telegram_message(
                telegram_token, telegram_chat_id, success_msg)

            return {
                "success": True,
                "url": final_url,
                "title": final_title
            }
        else:
            # 登录失败，截图
            screenshot_path = "login_failure_bot.png"
            try:
                driver.save_screenshot(screenshot_path)
                print(f"📸 失败截图已保存: {screenshot_path}")
            except Exception as e:
                print(f"⚠️  截图保存失败: {e}")

            error_msg = f"""*❌ 登录失败*

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 当前 URL: {final_url}
📄 标题: {final_title}
💡 提示: 可能是 reCAPTCHA 验证失败，请尝试更新 Cookie
"""
            print("❌ 登录失败：仍停留在登录页面")
            send_telegram_message(telegram_token, telegram_chat_id, error_msg)

            return {
                "success": False,
                "error": "Still on login page",
                "url": final_url
            }

    except Exception as e:
        error_msg = f"""*❌ 登录过程出错*

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚠️ 错误: {str(e)}
"""
        print(f"❌ 错误: {e}")

        # 尝试截图
        try:
            screenshot_path = "login_error_bot.png"
            driver.save_screenshot(screenshot_path)
            print(f"📸 错误截图已保存: {screenshot_path}")
        except Exception as screenshot_error:
            print(f"⚠️  截图保存失败: {screenshot_error}")

        send_telegram_message(telegram_token, telegram_chat_id, error_msg)

        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Luneshost 自动登录脚本 (Botasaurus)")
    print("=" * 50)
    print()

    # 运行登录任务
    result = login_task()

    print()
    print("=" * 50)
    if result and result.get('success'):
        print("✅ 脚本执行完成 - 登录成功")
        if result.get('method') == 'cookie':
            print("🍪 使用 Cookie 复用，无需登录验证")
        sys.exit(0)
    else:
        print("❌ 脚本执行完成 - 登录失败")
        print("💡 提示：运行 `python export_cookies.py` 导出新 Cookie")
        sys.exit(1)
