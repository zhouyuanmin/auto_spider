from selenium.common import exceptions
from selenium import webdriver
from pathlib import Path
from io import StringIO
import xlsxwriter
import traceback
import datetime
import logging
import random
import xlrd
import json
import time
import sys
import os
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auto_spider.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
from goods import models

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - line:%(lineno)d - %(levelname)s: %(message)s",
)

# 全局配置信息
base_dir = Path(__file__).resolve().parent
proxies = [
    "http://127.0.0.1:4780",
    "http://127.0.0.1:5780",
    "http://127.0.0.1:6780",
    "http://127.0.0.1:7780",
]
window_width, window_height = (1250, 900)  # 需要根据分辨率来确定窗口大小
synnex_username = "lwang@techfocusUSA.com"
synnex_password = "/4WM9ZAtB6c8ph6"
ingram_username = "lwang@techfocususa.com"
ingram_password = "3851330mM&"

# 业务配置
part_number_file = "part_number_file.txt"
effective_days = 7  # 刷新有效时间
gsa_source_level = 1  # gsa网站source最低值

# 页面节点
page_elements = {
    "login_email": '//*[@id="inputEmailAddress"]',
    "login_password": '//*[@id="inputPassword"]',
    "login_button": '//*[@id="loginBtn"]',
    "ingram_username": '//*[@id="okta-signin-username"]',
    "ingram_password": '//*[@id="okta-signin-password"]',
    "ingram_button": '//*[@id="okta-signin-submit"]',
    # "product_keywords": '//*[@id="searchText"]',
    # "part_search_button": '//*[@id="partSearchBtn"]',
    "product_items": '//*[@id="searchResultTbody"]/tr',
    "tbody": '//*[@id="resultList"]//tbody',
    # "product_href": '//*[@id="searchResultTbody"]/tr[1]/td/strong/a',
    "msrp": '//*[@class="msrp"]/span',
    "price_info": '//*[@class="price-info"]/a',
    "mfr_part_no": '//*[@id="searchResultTbody"]//tbody/tr[1]/td[1]/span',
    "search": '//*[@id="globalSearch"]',
    "product_list": '//*[@class="productListControl isList"]/app-ux-product-display-inline',
    "sources": './/span[@align="left"]',
    "item_a": './/div[@class="itemName"]//a',
    "mfr_name": './/div[@class="mfrName"]',
    "mfr_part_no_gsa": './/div[@class="mfrPartNumber"]',
    "product_name": '//h4[@role="heading"]',
    "product_description": '//div[@heading="Product Description"]/div',
    "description_strong": '//div[@heading="Vendor Description"]/strong',
    "description": '//div[@heading="Vendor Description"]/div',
    "gsa_advantage_price": '//table[@role="presentation"]/tbody//strong',
    "zip": '//input[@id="zip"]',
    "search_msrp": '//*[@id="search-container"]//div[@class="css-j7qwjs"]',
    "main_view": '//*[@id="main-view"]/div/div[1]/div/div[1]',
    "coo_divs": '//*[@id="main"]//li',
}


# 基础函数
def waiting_to_load(browser, count=10, sleep_time=1):
    """等待页面加载"""
    if sleep_time:
        time.sleep(sleep_time)
    while True:
        status = browser.execute_script("return document.readyState")
        if status == "complete":
            return True
        elif count <= 0:
            return False
        else:
            time.sleep(0.5)
            count -= 1


def scroll_to_bottom(browser, count=None):
    """滚动页面,到页面底部"""
    js = "return action=document.body.scrollHeight"
    height = 0
    new_height = browser.execute_script(js)

    while height < new_height:
        for i in range(height, new_height, 100):
            browser.execute_script("window.scrollTo(0, {})".format(i))
            time.sleep(0.5)
        browser.execute_script("window.scrollTo(0, {})".format(new_height - 1))
        height = new_height
        time.sleep(1)
        new_height = browser.execute_script(js)
        if count is None:
            continue
        else:
            count -= 1
            if count < 0:
                return False
    return True


def get_driver():
    if sys.platform.startswith("win32"):
        driver = os.path.join(base_dir, "chromedriver.exe")
    elif sys.platform.startswith("darwin"):
        driver = os.path.join(base_dir, "chromedriver")
    else:
        logging.error("不支持此类操作系统")
        sys.exit(0)
    return driver


def create_browser(index=0):
    """
    创建browser
    index: 0 默认使用第一个代理
    """
    global window_width
    global window_height
    global proxies
    options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values": {"notifications": 1}}
    options.add_experimental_option("prefs", prefs)
    options.add_argument(f"--proxy-server={proxies[index]}")

    driver = get_driver()
    browser = webdriver.Chrome(driver, options=options)
    x, y = random.randint(10, 600), random.randint(10, 20)
    x, y = 20, 20
    browser.set_window_rect(x, y, width=window_width, height=window_height)
    return browser


def save_error_screenshot(browser, sign, detail):
    """异常截图"""
    time_str = str(int(time.time() * 1000))
    file_name = f"{sign}_{time_str}_{detail}.png"
    file_name = os.path.join(base_dir, file_name)
    browser.get_screenshot_as_file(file_name)


# 业务基础函数
def login_synnex():
    global synnex_username
    global synnex_password
    browser = create_browser()
    try:
        browser.get("https://ec.synnex.com/ecx/login.html")
        waiting_to_load(browser)
    except exceptions.TimeoutException as e:
        logging.warning("打开页面超时,重试一次")
        browser.get("https://ec.synnex.com/ecx/login.html")
        waiting_to_load(browser)

    # 登录
    login_buttons = browser.find_elements_by_xpath(page_elements.get("login_email"))
    if login_buttons:
        login_email_textbox = browser.find_element_by_xpath(
            page_elements.get("login_email")
        )
        login_email_textbox.send_keys(synnex_username)
        waiting_to_load(browser)
        login_password_textbox = browser.find_element_by_xpath(
            page_elements.get("login_password")
        )
        login_password_textbox.send_keys(synnex_password)
        waiting_to_load(browser)
        login_button = browser.find_element_by_xpath(page_elements.get("login_button"))
        login_button.click()
        waiting_to_load(browser)
        return browser
    else:
        return browser


def login_ingram():
    global ingram_username
    global ingram_password
    browser = create_browser()
    try:
        browser.get("https://usa.ingrammicro.com/cep/app/login")
        waiting_to_load(browser)
    except exceptions.TimeoutException as e:
        logging.warning("打开页面超时,重试一次")
        browser.get("https://usa.ingrammicro.com/cep/app/login")
        waiting_to_load(browser)

    # 登录
    login_buttons = browser.find_elements_by_xpath(page_elements.get("ingram_username"))
    if login_buttons:
        login_email_textbox = browser.find_element_by_xpath(
            page_elements.get("ingram_username")
        )
        login_email_textbox.send_keys(ingram_username)
        waiting_to_load(browser)
        login_password_textbox = browser.find_element_by_xpath(
            page_elements.get("ingram_password")
        )
        login_password_textbox.send_keys(ingram_password)
        waiting_to_load(browser)
        login_button = browser.find_element_by_xpath(page_elements.get("ingram_button"))
        login_button.click()
        waiting_to_load(browser)
        return browser
    else:
        return browser


def get_part_numbers(path=part_number_file, distinct=False):
    """
    获取part_numbers
    path: txt文件 默认part_number_file文件
    distinct: False 默认不去重
    """
    part_numbers = []
    with open(path, "r") as f:
        for line in f.readlines():
            line = line.strip()
            if line:  # 不要空字符
                part_numbers.append(line)
    if distinct:
        part_numbers = list(set(part_numbers))
    return part_numbers


def refresh_synnex_good(part_number, browser):
    # TODO:
    pass


def refresh_synnex_goods(part_numbers) -> bool:
    """
    return: bool True表示所有数据都有效、False还有数据需要更新
    """
    # 找出待爬取的part_numbers
    now_time = datetime.datetime.now()
    effective_time = now_time - datetime.timedelta(days=7)
    exist_part_numbers = models.SynnexGood.objects.filter(
        refresh_at__gt=effective_time,  # 在有效期内
        status__isnull=False,  # 需要爬取过
    ).values_list("part_number", flat=True)
    part_numbers = set(part_numbers) - set(exist_part_numbers)
    part_numbers = list(part_numbers)

    if not part_numbers:
        return True

    # 开始爬取part_numbers
    browser = login_synnex()
    for part_number in part_numbers:
        refresh_synnex_good(part_number, browser)

    return False
