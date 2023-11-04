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
import time
import sys
import os
import re

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, "auto_spider"))  # 解决命令行运行问题

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auto_spider.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
from goods import models

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - line:%(lineno)d - %(levelname)s: %(message)s",
)

# 异常文件夹
ERROR_PATH = os.path.join(BASE_DIR, "auto_spider", "errors")
if not os.path.exists(ERROR_PATH):
    os.mkdir(ERROR_PATH)

# 全局配置信息
base_dir = Path(__file__).resolve().parent
proxies = [
    "http://127.0.0.1:4780",
    "http://127.0.0.1:5780",
    "http://127.0.0.1:6780",
    "http://127.0.0.1:7780",
]
window_width, window_height = (1250, 900)  # 需要根据分辨率来确定窗口大小
no_screenshot = True
synnex_username = "lwang@techfocusUSA.com"
synnex_password = "/4WM9ZAtB6c8ph6"
ingram_username = "lwang@techfocususa.com"
ingram_password = "3851330mM&"
synnex_part_number_file = os.path.join(ERROR_PATH, "synnex_part_number_file.txt")
gsa_part_number_file = os.path.join(ERROR_PATH, "gsa_part_number_file.txt")
gsa_url_file = os.path.join(ERROR_PATH, "gsa_url_file.txt")
ingram_part_number_file = os.path.join(ERROR_PATH, "ingram_part_number_file.txt")

# 业务配置
part_number_file = os.path.join(base_dir, "part_number_file.txt")
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
    "product_keywords": '//*[@id="searchText"]',
    # "part_search_button": '//*[@id="partSearchBtn"]',
    "product_items": '//*[@id="searchResultTbody"]/tr',
    "tbody": '//*[@id="resultList"]//tbody',
    # "product_href": '//*[@id="searchResultTbody"]/tr[1]/td/strong/a',
    "msrp": '//*[@class="msrp"]/span',
    "price_info": '//*[@class="price-info"]/a',
    "mfr_part_no": '//*[@id="searchResultTbody"]//strong[contains(text(),"Mfr.P/N:")]/following-sibling::span[1]',
    # "sku": '//*[@id="searchResultTbody"]/tr[1]/td[3]/table/tbody/tr[1]/td[2]',
    "mfr": '//*[@id="searchResultTbody"]//div[@class="company-name"]',
    "search": '//*[@id="globalSearch"]',
    "product_list": '//*[@class="productListControl isList"]/app-ux-product-display-inline',
    "zero_results": '//*[@id="zero-results-main"]//h4',
    "sources": './/span[@align="left"]',
    "item_a": './/div[@class="itemName"]//a',
    "mfr_name": './/div[@class="mfrName"]',
    "mfr_part_no_gsa": './/div[@class="mfrPartNumber"]',
    "product_name": '//h4[@role="heading"]',
    "all_description": '//div[@class="product-details-accordion"]',
    "product_description": '//div[@heading="Product Description"]/div',
    "description_strong": '//div[@heading="Vendor Description"]/strong',
    "description": '//div[@heading="Vendor Description"]/div',
    "gsa_advantage_price": '//table[@role="presentation"]/tbody//strong',
    "zip": '//input[@id="zip"]',
    "search_msrp": '//*[@id="search-container"]//div[@class="css-j7qwjs"]',
    "main_view": '//*[@id="main-view"]/div/div[1]/div/div[1]',
    "mas_sin": '//*[@id="main"]//strong[contains(text(),"MAS Schedule/SIN")]/../following-sibling::div[1]',
    "coo_divs": '//*[@id="main"]//strong[contains(text(),"Country of Origin")]/../following-sibling::div[1]',
    "manufacturer_divs": '//*[@id="main"]//strong[contains(text(),"Manufacturer")]/../following-sibling::div[1]',
    "vpn_divs": '//*[@id="main-view"]//span[contains(text(),"VPN:")]/following-sibling::span[1]',
    "no_results": '//*[@id="search-container"]//h1[contains(text(),"Sorry, no results found!")]',
    "own_price": '//*[@id="main-view"]//div[@class="ownPrice no-print css-lqai7o"]',
    "lw": '//*[@id="root"]/div/div[1]/div/div[3]/button[5]/div/span',
    "product_link": '//a[@data-name="productsearch_product_link"]',
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
    global no_screenshot
    if no_screenshot:
        return None

    time_str = str(int(time.time() * 1000))
    file_name = f"{sign}_{time_str}_{detail}.png"
    file_name = os.path.join(ERROR_PATH, file_name)
    browser.get_screenshot_as_file(file_name)


def get_data_by_excel(path, sheet_index=0, begin_row=1):
    """读取excel 返回所有行"""
    excel_data = xlrd.open_workbook(filename=path)
    table = excel_data.sheets()[sheet_index]
    data = []
    for i in range(begin_row, table.nrows):
        data.append(table.row_values(i))
    return data


def save_data_to_excel(path, data):
    """
    将data数据输出到excel
    data: [[1,2,3],[1,2,3]]
    path: xxx.xlsx
    """
    work_book = xlsxwriter.Workbook(path)
    work_sheet = work_book.add_worksheet()
    row = 0  # 表头从第0行开始写
    for line in data:
        col = 0
        for value in line:
            work_sheet.write(row, col, value)
            col += 1
        row += 1
    work_book.close()


# 业务基础函数
def text2dollar(text, sign=True):
    if sign and "$" not in text:  # 开启标志验证 则需要有$符号
        logging.error(text)
        raise ValueError(f"text={text}")
    # 提取价格
    text = text.replace(",", "")  # 处理逗号
    dollar = float(text.strip("$"))
    return dollar


def text2source(text):
    nums = re.findall(r"From (\d+) source", text)
    return int(nums[0])


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

    login_buttons = browser.find_elements_by_xpath(page_elements.get("ingram_username"))
    for i in range(3):  # 网很慢 刷新三次 还是无网页就算了
        if login_buttons:
            break
        else:
            time.sleep(3)
            login_buttons = browser.find_elements_by_xpath(
                page_elements.get("ingram_username")
            )
    else:
        logging.error(f"ingram无网页 登陆失败")
        return browser

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
        time.sleep(10)  # 登陆后 等待页面跳转
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
            line = line.replace(" ", "")  # 去掉部分中间有空格的
            line = line.strip()
            if line:  # 不要空字符
                part_numbers.append(line)
    if distinct:
        part_numbers = list(set(part_numbers))
    return part_numbers


def refresh_synnex_good(part_number, browser):
    """
    刷新 synnex_good
    爬过 不管是否有数据 都会刷新refresh_at
    """
    logging.info(f"刷新 synnex_good {part_number}")

    url = f"https://ec.synnex.com/ecx/part/searchResult.html?begin=0&offset=20&keyword={part_number}&sortField=reference_price&spaType=FG"
    browser.get(url)
    waiting_to_load(browser)

    search_divs = browser.find_elements_by_xpath(page_elements.get("product_keywords"))
    if not search_divs:  # 页面未加载完成
        raise ValueError(f"页面未加载完成 part_number={part_number}")

    time.sleep(10)  # 降低爬取速度

    # 最低价产品(已排序 取第一个)
    product_items = browser.find_elements_by_xpath(page_elements.get("product_items"))
    if product_items:
        msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        if not msrp_divs:
            time.sleep(3)
            msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        if msrp_divs:
            msrp = text2dollar(msrp_divs[0].text, True)
        else:
            raise ValueError(f"msrp值不存在 part_number={part_number}")

        federal_govt_price_divs = browser.find_elements_by_xpath(
            page_elements.get("price_info")
        )
        if not federal_govt_price_divs:
            time.sleep(3)
            federal_govt_price_divs = browser.find_elements_by_xpath(
                page_elements.get("price_info")
            )
        if federal_govt_price_divs:
            federal_govt_price = text2dollar(federal_govt_price_divs[0].text, True)
        else:
            raise ValueError(f"federal_govt_price值不存在 part_number={part_number}")

        mfr_p_n_divs = browser.find_elements_by_xpath(page_elements.get("mfr_part_no"))
        if mfr_p_n_divs:
            mfr_p_n = mfr_p_n_divs[0].text
        else:
            raise ValueError(f"mfr_p_n值不存在 part_number={part_number}")

        mfr_divs = browser.find_elements_by_xpath(page_elements.get("mfr"))
        if mfr_divs:
            mfr = mfr_divs[0].text
        else:
            raise ValueError(f"mfr值不存在 part_number={part_number}")

        # 刷新obj
        obj, _ = models.SynnexGood.objects.get_or_create(part_number=part_number)
        obj.mfr = mfr
        obj.msrp = msrp
        obj.federal_govt_price = federal_govt_price
        obj.status = True
        obj.refresh_at = datetime.datetime.now()
        obj.save()
    else:
        # 无产品
        tbody = browser.find_elements_by_xpath(page_elements.get("tbody"))
        if tbody:  # 页面正常
            text = tbody[0].text
            if "Your search found no result." in text:
                pass
            elif "in this page is excluded" in text:
                pass
            elif "in this page are excluded" in text:
                pass
            else:  # 其他情况
                raise ValueError(f"未知情况 part_number={part_number}")

            # 创建一个空的obj
            obj, _ = models.SynnexGood.objects.get_or_create(part_number=part_number)
            obj.status = False
            obj.refresh_at = datetime.datetime.now()
            obj.save()
        else:  # 页面异常
            raise ValueError(f"未知情况 part_number={part_number}")


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
    part_numbers.sort()

    if not part_numbers:
        return True
    logging.info(len(part_numbers))

    # 开始爬取part_numbers
    browser = login_synnex()
    for part_number in part_numbers:
        try:
            # 判断是否登陆了
            login_buttons = browser.find_elements_by_xpath(
                page_elements.get("login_email")
            )
            if login_buttons:  # 未登陆
                browser.quit()
                browser = login_synnex()

            time.sleep(30)  # 限制爬取速度 防止封号
            refresh_synnex_good(part_number, browser)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part_number}_{int(time.time())}"
            file_name = os.path.join(ERROR_PATH, file_name)
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            save_error_screenshot(browser, "synnex", part_number)

            global synnex_part_number_file
            with open(synnex_part_number_file, "a+") as f:
                f.write(f"{part_number}\n")

    return False


def refresh_gsa_good(part_number, browser):
    """
    刷新 gsa_good
    爬过 不管是否有数据 都会刷新refresh_at
    爬过 无数据则新增一个空obj
    爬过 有数据则会删除就数据 插入新数据
    """
    logging.info(f"刷新 gsa_good {part_number}")

    url = f"https://www.gsaadvantage.gov/advantage/ws/search/advantage_search?q=0:8{part_number}&db=0&searchType=0"
    browser.get(url)
    time.sleep(5)
    waiting_to_load(browser)

    search_divs = browser.find_elements_by_xpath(page_elements.get("search"))
    if not search_divs:  # 页面未加载完成
        raise ValueError(f"页面未加载完成 part_number={part_number}")

    time.sleep(2)  # 降低爬取速度

    product_divs = browser.find_elements_by_xpath(page_elements.get("product_list"))
    if not product_divs:  # 无产品列表
        zero_results_divs = browser.find_elements_by_xpath(
            page_elements.get("zero_results")
        )
        if zero_results_divs:  # 确实无产品 则创建空的obj
            # 创建一个空的obj
            obj, _ = models.GSAGood.objects.get_or_create(part_number=part_number)
            obj.refresh_at = datetime.datetime.now()
            obj.save()
        else:
            raise ValueError(f"未知情况 part_number={part_number}")

    # 有产品列表
    valid_source_urls = []
    first_source_urls = []
    for product_div in product_divs:
        mfr_part_number_div = product_div.find_element_by_xpath(
            page_elements.get("mfr_part_no_gsa")
        )
        mfr_part_number = mfr_part_number_div.text.strip()

        url_div = product_div.find_element_by_xpath(page_elements.get("item_a"))
        url = url_div.get_attribute("href")

        product_name = url_div.text

        mfr_div = product_div.find_element_by_xpath(page_elements.get("mfr_name"))
        mfr = mfr_div.text[4:].strip()

        source_divs = product_div.find_elements_by_xpath(page_elements.get("sources"))
        if not source_divs:  # 有些产品 没有sources
            logging.warning(f"有些产品没有sources part_number={part_number}")
            continue
            # raise ValueError(f"有些产品没有sources part_number={part_number}")
        source_div = product_div.find_element_by_xpath(page_elements.get("sources"))
        source = text2source(source_div.text)

        if source >= 1:  # 都爬取
            valid_source_urls.append([mfr_part_number, product_name, mfr, source, url])
        elif not first_source_urls:
            first_source_urls.append([mfr_part_number, product_name, mfr, source, url])

    # 排序,取前3
    valid_source_urls = sorted(
        valid_source_urls, key=lambda x: x[3], reverse=True
    )  # 使用source排序 从大到小
    if len(valid_source_urls) > 3:
        valid_source_urls = valid_source_urls[0:3]

    if not valid_source_urls:  # 如果没有符合要求的,则采集第一个产品
        valid_source_urls = first_source_urls

    gsa_data = []
    # 到详细页采集数据
    for (mfr_part_number, product_name, mfr, source, url) in valid_source_urls:
        browser.get(url)
        time.sleep(5)
        waiting_to_load(browser)

        # 增加判断是否需要邮编,有则跳过
        zip_div = browser.find_elements_by_xpath(page_elements.get("zip"))
        if zip_div:
            continue

        search_divs = browser.find_elements_by_xpath(page_elements.get("search"))
        if not search_divs:  # 页面未加载完成
            raise ValueError(f"页面未加载完成 part_number={part_number}")

        mas_sin_divs = browser.find_elements_by_xpath(page_elements.get("mas_sin"))
        if mas_sin_divs:
            mas_sin = mas_sin_divs[0].text.strip()
        else:
            raise ValueError(f"mas_sin不存在 part_number={part_number}")

        coo_divs = browser.find_elements_by_xpath(page_elements.get("coo_divs"))
        if coo_divs:
            coo = coo_divs[0].text.strip()
        elif mas_sin:  # 当coo不存在 但mas_sin存在 则设置coo为空字符串
            coo = ""
        else:
            raise ValueError(f"coo不存在 part_number={part_number}")

        description_div = browser.find_element_by_xpath(
            page_elements.get("all_description")
        )
        description = description_div.text
        if len(description) > 2047:
            description = description[0:2047]

        gsa_advantage_price_divs = browser.find_elements_by_xpath(
            page_elements.get("gsa_advantage_price")
        )
        gsa_advantage_price_divs = gsa_advantage_price_divs[1:]  # 去掉title
        gsa_advantage_prices = [0, 0, 0]
        for i, div in enumerate(gsa_advantage_price_divs):
            if i >= 3:  # 0,1,2
                break
            gsa_advantage_prices[i] = text2dollar(div.text)
        gsa_price_1, gsa_price_2, gsa_price_3 = gsa_advantage_prices

        gsa_row = [
            part_number,
            mfr_part_number,
            product_name,
            mfr,
            source,
            url,
            mas_sin,
            coo,
            description,
            gsa_price_1,
            gsa_price_2,
            gsa_price_3,
        ]
        gsa_data.append(gsa_row)

    if gsa_data:
        # 先删后增
        models.GSAGood.objects.filter(part_number=part_number).delete()
        gsa_objs = []
        for gsa_row in gsa_data:
            gsa_obj = models.GSAGood(
                part_number=gsa_row[0],
                mfr_part_number=gsa_row[1],
                product_name=gsa_row[2],
                mfr=gsa_row[3],
                source=gsa_row[4],
                url=gsa_row[5],
                mas_sin=gsa_row[6],
                coo=gsa_row[7],
                description=gsa_row[8],
                gsa_price_1=gsa_row[9],
                gsa_price_2=gsa_row[10],
                gsa_price_3=gsa_row[11],
            )
            gsa_objs.append(gsa_obj)
        models.GSAGood.objects.bulk_create(gsa_objs)
    else:
        # 没数据 详情页数据爬取失败的情况
        # 创建一个空的obj
        obj, _ = models.GSAGood.objects.get_or_create(part_number=part_number)
        obj.refresh_at = datetime.datetime.now()
        obj.save()


def refresh_gsa_goods(part_numbers, index=0) -> bool:
    """
    return: bool True表示所有数据都有效、False还有数据需要更新
    """
    # 找出待爬取的part_numbers
    now_time = datetime.datetime.now()
    effective_time = now_time - datetime.timedelta(days=7)
    exist_part_numbers = models.GSAGood.objects.filter(
        refresh_at__gt=effective_time  # 在有效期内
    ).values_list("part_number", flat=True)
    part_numbers = set(part_numbers) - set(exist_part_numbers)
    part_numbers = list(part_numbers)
    part_numbers.sort()

    if not part_numbers:
        return True
    logging.info(len(part_numbers))

    # 开始爬取part_numbers
    browser = create_browser(index)
    for part_number in part_numbers:
        try:
            refresh_gsa_good(part_number, browser)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part_number}_{int(time.time())}"
            file_name = os.path.join(ERROR_PATH, file_name)
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            save_error_screenshot(browser, "gsa", part_number)

            global gsa_part_number_file
            with open(gsa_part_number_file, "a+") as f:
                f.write(f"{part_number}\n")

    return False


def refresh_gsa_good_by_url(url, browser):
    """
    刷新 gsa_good_by_url
    爬过 不管是否有数据 都会刷新refresh_at
    """
    logging.info(f"刷新 gsa_good_by_url {url}")

    # 到详细页采集数据
    browser.get(url)
    time.sleep(5)
    waiting_to_load(browser)

    # 增加判断是否需要邮编,有则跳过
    zip_div = browser.find_elements_by_xpath(page_elements.get("zip"))
    if zip_div:
        raise ValueError(f"页面未加载完成 有邮编 url={url}")

    search_divs = browser.find_elements_by_xpath(page_elements.get("search"))
    if not search_divs:  # 页面未加载完成
        raise ValueError(f"页面未加载完成 url={url}")

    mas_sin_divs = browser.find_elements_by_xpath(page_elements.get("mas_sin"))
    if mas_sin_divs:
        mas_sin = mas_sin_divs[0].text.strip()
    else:
        raise ValueError(f"mas_sin不存在 url={url}")

    coo_divs = browser.find_elements_by_xpath(page_elements.get("coo_divs"))
    if coo_divs:
        coo = coo_divs[0].text.strip()
    elif mas_sin:  # 当coo不存在 但mas_sin存在 则设置coo为空字符串
        coo = ""
    else:
        raise ValueError(f"coo不存在 url={url}")

    description_div = browser.find_element_by_xpath(
        page_elements.get("all_description")
    )
    description = description_div.text
    if len(description) > 2047:
        description = description[0:2047]

    gsa_advantage_price_divs = browser.find_elements_by_xpath(
        page_elements.get("gsa_advantage_price")
    )
    gsa_advantage_price_divs = gsa_advantage_price_divs[1:]  # 去掉title
    gsa_advantage_prices = [0, 0, 0]
    for i, div in enumerate(gsa_advantage_price_divs):
        if i >= 3:  # 0,1,2
            break
        gsa_advantage_prices[i] = text2dollar(div.text)
    gsa_price_1, gsa_price_2, gsa_price_3 = gsa_advantage_prices

    manufacturer_divs = browser.find_elements_by_xpath(page_elements.get("manufacturer_divs"))
    if manufacturer_divs:
        manufacturer = manufacturer_divs[0].text.strip()
    else:
        raise ValueError(f"manufacturer不存在 url={url}")

    # 刷新此url的所有objs
    objs = models.GSAGood.objects.filter(url=url)
    for obj in objs:
        obj.mas_sin = mas_sin
        obj.coo = coo
        obj.description = description
        obj.gsa_price_1 = gsa_price_1
        obj.gsa_price_2 = gsa_price_2
        obj.gsa_price_3 = gsa_price_3
        obj.manufacturer = manufacturer
        obj.refresh_at = datetime.datetime.now()
        obj.save()


def refresh_gsa_goods_by_urls(url_txt_path, effective_time_str, index=0) -> bool:
    """
    url_txt_path: url文件
    effective_time_str: "2023-11-04 12:17:29"
    return: bool True表示所有数据都有效、False还有数据需要更新
    """
    # 找出待爬取的urls
    urls = get_part_numbers(url_txt_path, distinct=True)
    effective_time = datetime.datetime.strptime(effective_time_str, "%Y-%m-%d %H:%M:%S")
    exist_urls = models.GSAGood.objects.filter(
        refresh_at__gt=effective_time  # 在有效期内
    ).values_list("url", flat=True)
    urls = set(urls) - set(exist_urls)
    urls = list(urls)
    if index:  # 默认 0 或者 1
        urls.sort(reverse=True)
    else:
        urls.sort()

    if not urls:
        logging.info(f"{True}")
        return True
    logging.info(len(urls))

    # 开始爬取urls
    browser = create_browser(index)
    for url in urls:
        try:
            refresh_gsa_good_by_url(url, browser)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"url_{int(time.time())}"
            file_name = os.path.join(ERROR_PATH, file_name)
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            save_error_screenshot(browser, "gsa", "url")

            global gsa_url_file
            with open(gsa_url_file, "a+") as f:
                f.write(f"{url}\n")

    logging.info(f"{False}")
    return False


def refresh_ingram_good(part_number, browser):
    """
    刷新 ingram_good
    爬过 不管是否有数据 都会刷新refresh_at
    """
    logging.info(f"刷新 ingram_good {part_number}")

    url = f"https://usa.ingrammicro.com/cep/app/product/productsearch?displaytitle={part_number}&keywords={part_number}&sortBy=relevance&page=1&rowsPerPage=8"
    browser.get(url)
    time.sleep(15)  # 降低爬取速度
    waiting_to_load(browser)

    main_view_divs = browser.find_elements_by_xpath(page_elements.get("main_view"))
    for i in range(3):  # 网很慢 刷新三次 还是无网页就算了
        if main_view_divs:
            break
        else:
            time.sleep(3)
            main_view_divs = browser.find_elements_by_xpath(
                page_elements.get("main_view")
            )
    else:
        raise ValueError(f"ingram无网页 part_number={part_number}")

    # 无产品
    no_results_divs = browser.find_elements_by_xpath(page_elements.get("no_results"))
    if no_results_divs:  # 无产品 则创建空的obj
        # 创建一个空的obj
        obj, _ = models.IngramGood.objects.get_or_create(part_number=part_number)
        obj.status = False
        obj.refresh_at = datetime.datetime.now()
        obj.save()
        return None

    # 如果是列表页 则点击第一个进入详情页
    product_links = browser.find_elements_by_xpath(page_elements.get("product_link"))
    if product_links:
        product_links[0].click()
        time.sleep(3)
        waiting_to_load(browser)

    # 有产品
    time.sleep(7)
    vpn_divs = browser.find_elements_by_xpath(page_elements.get("vpn_divs"))
    if vpn_divs:
        vpn = vpn_divs[0].text.strip()
    else:
        raise ValueError(f"vpn不存在 part_number={part_number}")

    vpn_divs = browser.find_elements_by_xpath(page_elements.get("vpn_divs"))
    if vpn_divs:
        vpn = vpn_divs[0].text.strip()
    else:
        raise ValueError(f"vpn不存在 part_number={part_number}")

    price_divs = browser.find_elements_by_xpath(page_elements.get("own_price"))
    if price_divs:
        text = price_divs[0].text
        if text == "Not Available":
            price = 0
        else:
            price = text2dollar(text, True)
    elif vpn:  # 当price不存在 但vpn存在 则设置price为0
        price = 0
    else:
        raise ValueError(f"price不存在 part_number={part_number}")

    # 刷新obj
    obj, _ = models.IngramGood.objects.get_or_create(part_number=part_number)
    obj.vpn = vpn
    obj.price = price
    obj.status = True
    obj.refresh_at = datetime.datetime.now()
    obj.save()


def refresh_ingram_goods(part_numbers, debug=True) -> bool:
    """
    return: bool True表示所有数据都有效、False还有数据需要更新
    """
    # 找出待爬取的part_numbers
    now_time = datetime.datetime.now()
    effective_time = now_time - datetime.timedelta(days=7)
    exist_part_numbers = models.IngramGood.objects.filter(
        refresh_at__gt=effective_time,  # 在有效期内
        status__isnull=False,  # 需要爬取过
    ).values_list("part_number", flat=True)
    part_numbers = set(part_numbers) - set(exist_part_numbers)
    part_numbers = list(part_numbers)
    part_numbers.sort()

    if not part_numbers:
        return True
    logging.info(len(part_numbers))

    # 开始爬取part_numbers
    browser = login_ingram()
    for part_number in part_numbers:
        try:
            # 判断是否登陆了
            login_buttons = browser.find_elements_by_xpath(page_elements.get("lw"))
            if login_buttons and login_buttons[0].text == "LW":
                refresh_ingram_good(part_number, browser)
            else:  # 未登陆
                logging.error("Ingram登陆状态异常")
                if debug:
                    input("请输入任意键继续")
                else:
                    logging.error("Ingram账号退出")
                    browser.quit()  # 保持账号稳定 直接关闭
                    sys.exit(0)
                    # browser = login_ingram()  # 重新登陆
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part_number}_{int(time.time())}"
            file_name = os.path.join(ERROR_PATH, file_name)
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            save_error_screenshot(browser, "ingram", part_number)

            global ingram_part_number_file
            with open(ingram_part_number_file, "a+") as f:
                f.write(f"{part_number}\n")

    return False


def spider():
    """爬虫总开关"""
    file = part_number_file  # 可以直接修改
    part_numbers = get_part_numbers(file, distinct=True)
    status = True
    # status = refresh_synnex_goods(part_numbers) and status  # 不使用可以直接注释掉 账号被封了暂时用不了
    status = refresh_gsa_goods(part_numbers, 0) and status  # 不使用可以直接注释掉
    status = refresh_ingram_goods(part_numbers) and status  # 不使用可以直接注释掉
    logging.info(f"{status}")


def get_valid_part_number_txt(source_txt_path, filter_txt_path, valid_txt_path):
    """
    获取有效part_number.txt
    source_txt_path - filter_txt_path 再去重后 存入valid_txt_path
    source_txt_path: 源txt
    filter_txt_path: 过滤txt
    valid_txt_path: 有效txt
    """
    source_valid_parts = set(get_part_numbers(source_txt_path, distinct=True))
    filter_valid_parts = set(get_part_numbers(filter_txt_path, distinct=True))
    valid_valid_parts = source_valid_parts - filter_valid_parts
    with open(valid_txt_path, "w+") as f:
        for part_number in valid_valid_parts:
            f.write(f"{part_number}\n")


def export(input_xlsx_path, output_xlsx_path, valid_txt_path, row_index, sheet_index=0, begin_row=0):
    """
    导出xlsx
    input_xlsx_path: 原文件
    output_xlsx_path: 输出文件
    valid_txt_path: 需要保留的part_numbers
    row_index: part_number所在列
    """
    part_numbers = get_part_numbers(valid_txt_path)
    part_number_set = set(part_numbers)

    new_data = []
    data = get_data_by_excel(input_xlsx_path, sheet_index, begin_row)
    row_title = data[0]
    synnex_titles = ["mfr", "mfr_p_n", "msrp", "federal_govt_price"]
    gsa_titles = [
        "mfr_part_number",
        "product_name",
        "mfr",
        "source",
        "url",
        "mas_sin",
        "coo",
        "description",
        "gsa_price_1",
        "gsa_price_2",
        "gsa_price_3",
        "manufacturer",
    ]
    ingram_titles = ["vpn", "price"]
    row_title.extend(synnex_titles)
    row_title.extend(gsa_titles)
    row_title.extend(ingram_titles)

    new_data.append(row_title)
    for row in data[1:]:
        part_number = row[row_index]
        if part_number in part_number_set:
            part_number_set.discard(part_number)
        else:
            continue

        # 在row的后面添加爬取的数据 并放入new_data
        synnex_obj, _ = models.SynnexGood.objects.get_or_create(part_number=part_number)
        synnex_fields = [
            synnex_obj.mfr,
            synnex_obj.mfr_p_n,
            synnex_obj.msrp,
            synnex_obj.federal_govt_price,
        ]

        ingram_obj, _ = models.IngramGood.objects.get_or_create(part_number=part_number)
        ingram_fields = [ingram_obj.vpn, ingram_obj.price]

        gsa_objs = models.GSAGood.objects.filter(part_number=part_number)
        if not gsa_objs:
            gsa_obj, _ = models.GSAGood.objects.get_or_create(part_number=part_number)
            gsa_objs = [gsa_obj]

        for gsa_obj in gsa_objs:
            gsa_fields = [
                gsa_obj.mfr_part_number,
                gsa_obj.product_name,
                gsa_obj.mfr,
                gsa_obj.source,
                gsa_obj.url,
                gsa_obj.mas_sin,
                gsa_obj.coo,
                gsa_obj.description,
                gsa_obj.gsa_price_1,
                gsa_obj.gsa_price_2,
                gsa_obj.gsa_price_3,
                gsa_obj.manufacturer,
            ]
            new_row = row + synnex_fields + gsa_fields + ingram_fields
            new_data.append(new_row)

    save_data_to_excel(output_xlsx_path, new_data)


def export_add_gsa_by_url(input_xlsx_path, output_xlsx_path, valid_txt_path, row_index, sheet_index=0, begin_row=0):
    """
    导出xlsx
    input_xlsx_path: 原文件
    output_xlsx_path: 输出文件
    valid_txt_path: 需要保留的part_numbers
    row_index: url所在列
    """
    urls = get_part_numbers(valid_txt_path)
    urls_set = set(urls)

    new_data = []
    data = get_data_by_excel(input_xlsx_path, sheet_index, begin_row)
    row_title = data[0]
    gsa_titles = [
        "mfr_part_number",
        "product_name",
        "mfr",
        "source",
        "url",
        "mas_sin",
        "coo",
        "description",
        "gsa_price_1",
        "gsa_price_2",
        "gsa_price_3",
        "manufacturer",
    ]
    row_title.extend(gsa_titles)
    new_data.append(row_title)

    for row in data[1:]:
        url = row[row_index]
        # 在row的后面添加爬取的数据 并放入new_data
        if url in urls_set:
            urls_set.discard(url)
        else:
            continue
        gsa_obj = models.GSAGood.objects.filter(url=url).first()
        gsa_fields = [
            gsa_obj.mfr_part_number,
            gsa_obj.product_name,
            gsa_obj.mfr,
            gsa_obj.source,
            gsa_obj.url,
            gsa_obj.mas_sin,
            gsa_obj.coo,
            gsa_obj.description,
            gsa_obj.gsa_price_1,
            gsa_obj.gsa_price_2,
            gsa_obj.gsa_price_3,
            gsa_obj.manufacturer,
        ]
        new_row = row + gsa_fields
        new_data.append(new_row)

    save_data_to_excel(output_xlsx_path, new_data)


if __name__ == "__main__":
    spider()
