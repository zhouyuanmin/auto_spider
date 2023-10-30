"""旧的代码文件,现在已经不适用了"""
from django.db.models import Sum
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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spider.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
from goods.models import Good, ECGood, GSAGood
from goods import models

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - line:%(lineno)d - %(levelname)s: %(message)s",
)

# 全局配置信息
base_dir = Path(__file__).resolve().parent
proxy = "http://127.0.0.1:4780"
window_width, window_height = (1250, 900)  # 需要根据分辨率来确定窗口大小
cookies_path = os.path.join(base_dir, "cookies.txt")
login_email = "lwang@techfocusUSA.com"
login_password = "/4WM9ZAtB6c8ph6"
gsa_source_level = 3  # gsa网站source最低值

# 页面节点
page_elements = {
    "login_email": '//*[@id="inputEmailAddress"]',
    "login_password": '//*[@id="inputPassword"]',
    "login_button": '//*[@id="loginBtn"]',
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


# 业务基础函数
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


def create_browser():
    global window_width
    global window_height
    options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values": {"notifications": 1}}
    options.add_experimental_option("prefs", prefs)
    options.add_argument(f"--proxy-server={proxy}")

    driver = get_driver()
    browser = webdriver.Chrome(driver, options=options)
    x, y = random.randint(10, 600), random.randint(10, 20)
    x, y = 20, 20
    browser.set_window_rect(x, y, width=window_width, height=window_height)
    return browser


def login(check=True):
    browser = create_browser()
    try:
        browser.get("https://ec.synnex.com/ecx/login.html")
        waiting_to_load(browser)
    except exceptions.TimeoutException as e:
        logging.warning("打开页面超时,重试一次")
        browser.get("https://ec.synnex.com/ecx/login.html")
        waiting_to_load(browser)

    browser.delete_all_cookies()
    with open(cookies_path, "r") as f:
        cookies_str = f.read()
        cookies = json.loads(cookies_str)
    for cookie in cookies:
        browser.add_cookie(cookie)
    browser.get("https://ec.synnex.com/ecx/landing.html")

    if not waiting_to_load(browser, sleep_time=5):
        browser.get("https://ec.synnex.com/ecx/landing.html")
        waiting_to_load(browser, sleep_time=5)

    if not check:  # 不判断登录状态
        return browser

    # 判断登录状态
    login_buttons = browser.find_elements_by_xpath(page_elements.get("login_email"))
    if login_buttons:
        login_email_textbox = browser.find_element_by_xpath(
            page_elements.get("login_email")
        )
        login_email_textbox.send_keys(login_email)
        login_password_textbox = browser.find_element_by_xpath(
            page_elements.get("login_password")
        )
        login_password_textbox.send_keys(login_password)
        login_button = browser.find_element_by_xpath(page_elements.get("login_button"))
        login_button.click()
        waiting_to_load(browser)
        return browser
    else:
        return browser


def update_cookies(browser):
    cookies = browser.get_cookies()
    cookies_str = json.dumps(cookies)
    with open(cookies_path, "w") as f:
        f.write(cookies_str)
    return True


def get_dollar(text):
    if "$" not in text:
        logging.error(text)
        raise
    else:
        text = text.replace(",", "")  # 处理逗号
        dollar = float(text.strip("$"))
    return dollar


def get_msrp(text):
    _text = re.findall(r"\$[\d.,]+", text)
    if _text:
        return get_dollar(_text[0])
    # logging.error(text)
    return 0


def get_num(text):
    num = re.findall(r"\d+", text)
    if num:
        return int(num[0])
    else:
        logging.error(text)
        raise


def save_error_screenshot(browser, sign, detail):
    time_str = str(int(time.time() * 1000))
    file_name = f"{sign}_{time_str}_{detail}.png"
    file_name = os.path.join(base_dir, "error", file_name)
    browser.get_screenshot_as_file(file_name)


# 业务逻辑函数
def get_data(path, begin_line=0, count=None, part_line=1, manufacturer_line=2):
    excel_data = xlrd.open_workbook(filename=path)
    table = excel_data.sheets()[0]  # 第一个table
    parts = table.col_values(part_line)[begin_line:]  # 第2列
    manufacturers = table.col_values(manufacturer_line)[begin_line:]  # 第3列
    zipped = zip(parts, manufacturers)
    zipped = list(zipped)
    if count:
        zipped = zipped[:count]
    return zipped


def get_data_by_excel(path, begin_row, cols):
    excel_data = xlrd.open_workbook(filename=path)
    table = excel_data.sheets()[0]  # 第一个table
    data = []
    for i in cols:
        data.append(table.col_values(i)[begin_row:])
    return data


def save_data_to_excel(path, data):
    work_book = xlsxwriter.Workbook(path)
    work_sheet = work_book.add_worksheet()
    row = 0  # 表头从第行列开始写
    for line in data:
        col = 0
        for value in line:
            work_sheet.write(row, col, value)
            col += 1
        row += 1
    work_book.close()


def get_model_param_by_ec(browser, part, manufacturer):
    """自带更新操作"""
    try:
        obj = ECGood.objects.get(part=part)
        if obj.ec_status:
            return
        if obj.federal_govt_spa or obj.msrp:
            obj.ec_status = True
            obj.save()
            return
        # return {}  # 存在则不需要再爬取
        logging.warning(f"EC:part={part},存在,需要更新数据")
    except ECGood.DoesNotExist:
        logging.warning(f"EC:part={part},不存在,需要爬取数据")
        pass
    # 判断是否需要登陆
    login_buttons = browser.find_elements_by_xpath(page_elements.get("login_email"))
    if login_buttons:
        logging.error("重新登陆")
        sys.exit(0)
    # 搜索与排序:PriceType=FederalGovtSPA,SortBy=Price(LowToHigh)
    url = f"https://ec.synnex.com/ecx/part/searchResult.html?begin=0&offset=20&keyword={part}&sortField=reference_price&spaType=FG"
    browser.get(url)
    waiting_to_load(browser)

    # 最低价产品(第一个)
    product_items = browser.find_elements_by_xpath(page_elements.get("product_items"))
    if product_items:
        msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        if not msrp_divs:
            time.sleep(3)
            msrp_divs = browser.find_elements_by_xpath(page_elements.get("msrp"))
        if msrp_divs:
            msrp = get_dollar(msrp_divs[0].text)
        else:
            # save_error_screenshot(browser, "ec", f"{part}_msrp")
            msrp = 0

        federal_govt_spa_divs = browser.find_elements_by_xpath(
            page_elements.get("price_info")
        )
        if not federal_govt_spa_divs:
            time.sleep(3)
            federal_govt_spa_divs = browser.find_elements_by_xpath(
                page_elements.get("price_info")
            )
        if federal_govt_spa_divs:
            federal_govt_spa = get_dollar(federal_govt_spa_divs[0].text)
        else:
            federal_govt_spa = 0

        mfr_part_no_divs = browser.find_elements_by_xpath(
            page_elements.get("mfr_part_no")
        )
        if mfr_part_no_divs:
            mfr_part_no = mfr_part_no_divs[0].text
        else:
            mfr_part_no = ""
        vendor_part_no = mfr_part_no
        # 直接处理
        try:
            obj = ECGood.objects.get(part=part)
        except ECGood.DoesNotExist:
            obj = ECGood(
                part=part,
                manufacturer=manufacturer,
                mfr_part_no=mfr_part_no,
                vendor_part_no=vendor_part_no,
                msrp=msrp,
                federal_govt_spa=federal_govt_spa,
                ec_status=True,
            )
            obj.save()
        except:
            pass
        else:
            obj.mfr_part_no = mfr_part_no
            obj.vendor_part_no = vendor_part_no
            obj.msrp = msrp
            obj.federal_govt_spa = federal_govt_spa
            obj.ec_status = True
            obj.save()
        return {
            "mfr_part_no": mfr_part_no,
            "vendor_part_no": vendor_part_no,
            "msrp": msrp,
            "federal_govt_spa": federal_govt_spa,
        }
    else:
        # 无产品
        tbody = browser.find_elements_by_xpath(page_elements.get("tbody"))
        if tbody:  # 页面正常
            text = tbody[0].text
            if "Your search found no result." in text:
                try:
                    obj, _ = ECGood.objects.get_or_create(part=part)
                    obj.manufacturer = manufacturer
                    obj.ec_status = True
                    obj.save()
                except ECGood.DoesNotExist:
                    pass
                except:
                    pass
        else:  # 页面异常
            return {}


def get_model_param_by_gsa(browser, part):
    objs = GSAGood.objects.filter(part=part)
    if objs:
        return {}  # 存在则不需要再爬取
    else:
        logging.warning(f"GSA:part={part},不存在,需要爬取数据")
    # 搜索
    url = f"https://www.gsaadvantage.gov/advantage/ws/search/advantage_search?q=0:8{part}&db=0&searchType=0"
    browser.get(url)
    time.sleep(5)
    waiting_to_load(browser)

    product_divs = browser.find_elements_by_xpath(page_elements.get("product_list"))
    if product_divs:
        pass
    else:
        # 判断页面是否加载完成
        search_divs = browser.find_elements_by_xpath(page_elements.get("search"))
        if search_divs:
            product_divs = browser.find_elements_by_xpath(
                page_elements.get("product_list")
            )
            if not product_divs:
                return {}
        else:
            return {}

    if product_divs:
        valid_source_urls = []
        first_source_urls = []
        for product_div in product_divs:
            source_divs = product_div.find_elements_by_xpath(
                page_elements.get("sources")
            )
            if not source_divs:  # 有些产品,没有sources
                continue
            source_div = product_div.find_element_by_xpath(page_elements.get("sources"))
            source = get_num(source_div.text)
            url_div = product_div.find_element_by_xpath(page_elements.get("item_a"))
            url = url_div.get_attribute("href")
            product_name = url_div.text  # 有问题,取里面的数据
            mfr_name_div = product_div.find_element_by_xpath(
                page_elements.get("mfr_name")
            )
            manufacturer_name = mfr_name_div.text[4:].strip()
            # mfr_part_no_gsa字段
            mfr_part_no_gsa_div = product_div.find_element_by_xpath(
                page_elements.get("mfr_part_no_gsa")
            )
            mfr_part_no_gsa = mfr_part_no_gsa_div.text.strip()
            if source >= gsa_source_level:
                valid_source_urls.append(
                    [source, url, product_name, manufacturer_name, mfr_part_no_gsa]
                )
            elif not first_source_urls:
                first_source_urls.append(
                    [source, url, product_name, manufacturer_name, mfr_part_no_gsa]
                )
        # 排序,取前3
        valid_source_urls = sorted(valid_source_urls, key=lambda x: x[0], reverse=True)
        if len(valid_source_urls) > 3:
            valid_source_urls = valid_source_urls[0:3]

        if not valid_source_urls:  # 如果没有符合要求的,则采集第一个产品
            valid_source_urls = first_source_urls

        gsa_data = []
        # 到详细页采集数据
        for (
            source,
            url,
            product_name,
            manufacturer_name,
            mfr_part_no_gsa,
        ) in valid_source_urls:
            browser.get(url)
            waiting_to_load(browser)

            # # product_name 取里面的
            # product_name_divs = browser.find_elements_by_xpath(
            #     page_elements.get("product_name")
            # )
            # if product_name_divs:
            #     product_name = product_name_divs[0].text

            description_divs = browser.find_elements_by_xpath(
                page_elements.get("description")
            )
            if not description_divs:
                waiting_to_load(browser)
                time.sleep(10)
                # 增加判断是否需要邮编,有则跳过
                zip_div = browser.find_elements_by_xpath(page_elements.get("zip"))
                if zip_div:
                    continue
            description_divs = browser.find_elements_by_xpath(
                page_elements.get("description")
            )
            if not description_divs:
                continue

            # 获取Country of Origin（coo）
            coo = ""
            divs = browser.find_elements_by_xpath(page_elements.get("coo_divs"))
            for div in divs:
                text = div.text
                if "Country of Origin" in text:
                    coo = text[18:].strip()

            description_div = browser.find_element_by_xpath(
                page_elements.get("description")
            )
            browser.execute_script(
                "window.scrollTo(0, {})".format(description_div.location.get("y") - 160)
            )
            _description_divs = browser.find_elements_by_xpath(
                page_elements.get("product_description")
            )
            if _description_divs:
                _product_description = _description_divs[0].text
            else:
                _product_description = ""
            product_description2 = _product_description

            _description_divs_strong = browser.find_elements_by_xpath(
                page_elements.get("description_strong")
            )
            if _description_divs_strong:
                product_description2_strong = _description_divs_strong[0].text
            else:
                product_description2_strong = ""

            waiting_to_load(browser)
            product_description = description_div.text
            gsa_advantage_price_divs = browser.find_elements_by_xpath(
                page_elements.get("gsa_advantage_price")
            )[1:]
            gsa_advantage_prices = [0, 0, 0]
            for i, div in enumerate(gsa_advantage_price_divs):
                if i >= 3:  # 0,1,2
                    break
                text = div.text
                if "$" in text:
                    gsa_advantage_prices[i] = get_dollar(text)
            product_description = (
                product_description
                if len(product_description) < 254
                else product_description[0:254]
            )
            product_description2_strong = (
                product_description2_strong
                if len(product_description2_strong) < 254
                else product_description2_strong[0:254]
            )
            product_description2 = (
                product_description2
                if len(product_description2) < 254
                else product_description2[0:254]
            )
            item_data = {
                "part": part,
                "manufacturer_name": manufacturer_name,
                "product_name": product_name,
                "product_description": product_description,
                "product_description2_strong": product_description2_strong,
                "product_description2": product_description2,
                "gsa_advantage_price_1": gsa_advantage_prices[0],
                "gsa_advantage_price_2": gsa_advantage_prices[1],
                "gsa_advantage_price_3": gsa_advantage_prices[2],
                "coo": coo,
                "mfr_part_no_gsa": mfr_part_no_gsa,
                "url": url,
                "source": source,
            }
            # 直接存储
            obj = GSAGood(**item_data)
            obj.save()
            gsa_data.append(item_data)
        return gsa_data
    else:
        logging.warning(f"part={part}无产品")
        return []


def get_model_param_by_inm(browser, part):
    try:
        obj = ECGood.objects.get(part=part)
        if obj.inm_status:
            return
        if obj.ingram_micro_price:
            obj.inm_status = True
            obj.save()
            return
        logging.warning(f"INM:part={part},存在,需要更新数据")
    except ECGood.DoesNotExist:
        logging.warning(f"INM:part={part},不存在,需要爬取数据")
        pass
    url = f"https://usa.ingrammicro.com/cep/app/product/productsearch?displaytitle={part}&keywords={part}&sortBy=relevance&page=1&rowsPerPage=8"
    browser.get(url)
    waiting_to_load(browser)

    # 判断网页是否加载完成
    main_view_divs = []
    for i in range(3):
        main_view_divs = browser.find_elements_by_xpath(page_elements.get("main_view"))
        if main_view_divs:
            break
        else:
            time.sleep(3)
    if not main_view_divs:
        logging.error(f"inm_{part}_load_page")

    search_msrp_divs = browser.find_elements_by_xpath(page_elements.get("search_msrp"))
    if search_msrp_divs:
        pass
    else:
        time.sleep(5)
        search_msrp_divs = browser.find_elements_by_xpath(
            page_elements.get("search_msrp")
        )
    if search_msrp_divs:
        time.sleep(3)
        text = search_msrp_divs[0].text
        ingram_micro_price = get_msrp(text)
        obj, _ = ECGood.objects.get_or_create(part=part)
        obj.inm_status = True
        obj.ingram_micro_price = ingram_micro_price
        obj.save()
        return {"ingram_micro_price": ingram_micro_price}
    else:
        return {}


def save_to_model(params):
    source = params.pop("source")
    url = params.pop("url")
    note_kv = {"source": source, "url": url}
    params["note"] = json.dumps(note_kv)
    good = Good(**params)
    good.save()


def save_to_model_ec(params):
    ec_good = ECGood(**params)
    ec_good.save()


def save_to_model_inm(part, ingram_micro_price):
    objs = Good.objects.filter(part=part)
    objs.update(ingram_micro_price=ingram_micro_price)


def spider():
    # 浏览器准备
    browser_ec = login()
    browser_gsa = create_browser()
    browser_inm = create_browser()
    # 数据准备
    begin_row = 1
    data = get_data_by_excel(
        "1.xlsx",
        begin_row=begin_row,
        cols=[1, 0],
    )
    parts = data[0]
    manufacturers = data[1]
    for i, part in enumerate(parts):
        if not part:  # 处理空格
            continue
        # 处理float数
        if isinstance(part, float):
            part = str(int(part))
        logging.info(f"index={i}:{i + begin_row},part:{part}")
        try:
            data_ec = get_model_param_by_ec(browser_ec, part, manufacturers[i])
            data_gsa_list = get_model_param_by_gsa(browser_gsa, part)
            data_inm = get_model_param_by_inm(browser_inm, part)
        except Exception as e:
            logging.error(e)
            error_file = StringIO()
            traceback.print_exc(file=error_file)
            details = error_file.getvalue()
            file_name = f"{part}_{int(time.time())}"
            with open(f"{file_name}.txt", "w") as f:
                f.write(details)
            sys.exit(0)


def ec_old2new():
    objs = Good.objects.all()
    for obj in objs:
        if ECGood.objects.filter(part=obj.part).exists():
            logging.warning(f"{obj.pk}")
            continue
        else:
            logging.info(f"{obj.pk}")
            ec_obj = ECGood()
            ec_obj.part = obj.part
            ec_obj.manufacturer = obj.manufacturer
            ec_obj.mfr_part_no = obj.mfr_part_no
            ec_obj.vendor_part_no = obj.vendor_part_no
            ec_obj.msrp = obj.msrp
            ec_obj.federal_govt_spa = obj.federal_govt_spa
            ec_obj.ingram_micro_price = obj.ingram_micro_price
            if obj.federal_govt_spa:
                ec_obj.ec_status = True
            if obj.ingram_micro_price:
                ec_obj.inm_status = True
            ec_obj.save()


def export(path, begin_row, begin_col, end_col, part_col, process=True):
    cols = list(range(begin_col, end_col + 1))
    excel_data = get_data_by_excel(path, begin_row, cols)
    parts = excel_data[part_col]
    data = []
    for i, part in enumerate(parts):
        if not part:
            continue
        if isinstance(part, float):
            part = str(int(part))
        row_data = []
        for item in excel_data:
            row_data.append(item[i])
        if i == 0:
            row_data.extend(
                [
                    "part",
                    "manufacturer",
                    "mfr_part_no",
                    "vendor_part_no",
                    "msrp",
                    "federal_govt_spa",
                    "ingram_micro_price",
                    # gsa
                    "manufacturer_name",
                    "product_name",
                    "product_description",
                    "product_description2_strong",
                    "product_description2",
                    "gsa_advantage_price_1",
                    "gsa_advantage_price_2",
                    "gsa_advantage_price_3",
                    "coo",
                    "mfr_part_no_gsa",
                    "url",
                    "source",
                    "min_price",
                    "description",
                ]
            )
            data.append(row_data)
            continue
        # 处理数据
        ec_objs = ECGood.objects.filter(part=part)
        if ec_objs:
            ec_obj = ec_objs[0]
        else:
            if process:
                continue
            else:
                ec_obj = ECGood(part=part)
        if ec_obj.federal_govt_spa == 0 and ec_obj.ingram_micro_price == 0:
            if process:
                continue
            else:
                pass
        gsa_objs = GSAGood.objects.filter(part=part)
        if (not process) and (not gsa_objs):
            gsa_obj = GSAGood(part=part)
            gsa_objs = [gsa_obj]

        for gsa_obj in gsa_objs:
            _row_data = []
            _row_data.extend(row_data)
            gsa_advantage_price_2 = float(gsa_obj.gsa_advantage_price_2)
            # 判断数值是否合理
            min_price = 0
            if (
                ec_obj.federal_govt_spa
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                min_price = ec_obj.federal_govt_spa
            if (
                ec_obj.ingram_micro_price
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                if min_price == 0:
                    min_price = ec_obj.ingram_micro_price
                else:
                    min_price = min(min_price, ec_obj.ingram_micro_price)
            if min_price or (not process):  # 数据合理
                # 处理描述
                description = ""
                if gsa_obj.product_description:
                    description = gsa_obj.product_description
                elif gsa_obj.product_description2:
                    description = gsa_obj.product_description2
                    if gsa_obj.product_description2_strong:
                        strong = (
                            gsa_obj.product_description2_strong.split("by")[-1]
                            .strip()
                            .strip(".")
                        )
                        description = description.replace(strong, "TechFocus LLC")
                    if "For further" in description:
                        description = description.split("For further")[0]
                    description += "For further information contact TechFocus at 304-906-8124 Or email lwang@techfocusUSA.com"
                else:
                    description = ""
                # 加数据
                _row_data.append(ec_obj.part)
                _row_data.append(ec_obj.manufacturer)
                _row_data.append(ec_obj.mfr_part_no)
                _row_data.append(ec_obj.vendor_part_no)
                _row_data.append(ec_obj.msrp)
                _row_data.append(ec_obj.federal_govt_spa)
                _row_data.append(ec_obj.ingram_micro_price)

                _row_data.append(gsa_obj.manufacturer_name)
                _row_data.append(gsa_obj.product_name)
                _row_data.append(gsa_obj.product_description)
                _row_data.append(gsa_obj.product_description2_strong)
                _row_data.append(gsa_obj.product_description2)
                _row_data.append(gsa_obj.gsa_advantage_price_1)
                _row_data.append(gsa_obj.gsa_advantage_price_2)
                _row_data.append(gsa_obj.gsa_advantage_price_3)
                _row_data.append(gsa_obj.coo)
                _row_data.append(gsa_obj.mfr_part_no_gsa)
                _row_data.append(gsa_obj.url)
                _row_data.append(gsa_obj.source)
                _row_data.append(min_price)
                _row_data.append(description)
                data.append(_row_data)

    save_data_to_excel("_done_未筛选.xlsx", data)


def import_order_filled(path, begin_row, begin_col, end_col):
    cols = list(range(begin_col, end_col + 1))
    excel_data = get_data_by_excel(path, begin_row, cols)
    parts = excel_data[2]
    data = []
    for i, part in enumerate(parts):
        row_data = []
        for item in excel_data:
            row_data.append(item[i])
        data.append(row_data)
    for i, _ in enumerate(data):
        print(i, _)

        part = _[2]
        if isinstance(part, float):
            part = str(int(part))

        models.OrderFilled.objects.create(
            contractor_name=_[0],
            contract_number=_[1],
            mfr_part_number=part,
            item_name=_[3],
            mfr_name=_[4],
            date=datetime.datetime.now(),
            unit_price=_[6],
            quantity=_[7],
            extended_price=_[8],
        )


def order_filled_to_order_good():
    objs = models.OrderFilled.objects.all()
    mfr_part_numbers = objs.values_list("mfr_part_number", flat=True)
    mfr_part_numbers = set(list(mfr_part_numbers))
    # print(mfr_part_numbers)
    objs_list = []
    for part in mfr_part_numbers:
        print(part)
        _obj = objs.filter(mfr_part_number=part).first()
        obj = models.OrderGood(
            contractor_name=_obj.contractor_name,
            contract_number=_obj.contract_number,
            mfr_part_number=_obj.mfr_part_number,
            item_name=_obj.item_name,
            mfr_name=_obj.mfr_name,
        )
        objs_list.append(obj)
        if len(objs_list) >= 500:
            models.OrderGood.objects.bulk_create(objs_list)
            objs_list = []
    models.OrderGood.objects.bulk_create(objs_list)


def order_filled_stat():
    """成交单统计"""
    order_filled_objs = models.OrderFilled.objects.all()
    order_good_objs = models.OrderGood.objects.all()
    id_mfr_part_numbers = list(order_good_objs.values_list("id", "mfr_part_number"))

    for i, part in id_mfr_part_numbers:
        print(i, part)
        kys = (
            order_filled_objs.filter(mfr_part_number=part)
            .values("unit_price")
            .annotate(quantity=Sum("quantity"))
            .order_by("unit_price")
        )
        order_filled_stat_objs = []
        for _ in kys:
            unit_price = _.get("unit_price")
            quantity = _.get("quantity")
            obj = models.OrderFilledStat(
                mfr_part_number=part,
                unit_price=unit_price,
                quantity=quantity,
                extended_price=unit_price * quantity,
            )
            order_filled_stat_objs.append(obj)
        models.OrderFilledStat.objects.bulk_create(order_filled_stat_objs)


def order_filled_stat2():
    """成交单统计2"""
    order_filled_stat_objs = models.OrderFilledStat.objects.all()
    kv_objs = order_filled_stat_objs.values("mfr_part_number").annotate(
        extended_price_sum=Sum("extended_price")
    )
    kvs = {}
    for _ in kv_objs:
        kvs[_.get("mfr_part_number")] = _.get("extended_price_sum")

    order_good_objs = models.OrderGood.objects.all()
    objs_list = []
    for order_good_obj in order_good_objs:
        logging.info(order_good_obj.pk)
        order_good_obj.extended_price = kvs.get(order_good_obj.mfr_part_number)
        objs_list.append(order_good_obj)
        if len(objs_list) >= 500:
            models.OrderGood.objects.bulk_update(objs_list, fields=["extended_price"])
            objs_list = []
    models.OrderGood.objects.bulk_update(objs_list, fields=["extended_price"])


def export_stat(export_path="1.xlsx"):
    order_good_objs = models.OrderGood.objects.all().order_by("-extended_price")
    data = []
    title = [
        "contractor_name",
        "contract_number",
        "mfr_part_number",
        "item_name",
        "mfr_name",
        "extended_price",  # 总价
        "unit_price",
        "quantity",
        "extended_price",  # 分总价
    ]
    data.append(title)

    order_filled_stat_objs = models.OrderFilledStat.objects.all()
    for order_good_obj in order_good_objs:
        logging.info(order_good_obj.pk)
        row_data_first_1 = [
            order_good_obj.contractor_name,
            order_good_obj.contract_number,
            order_good_obj.mfr_part_number,
            order_good_obj.item_name,
            order_good_obj.mfr_name,
            order_good_obj.extended_price,
        ]
        row_data_first_2 = ["", "", "", "", "", ""]
        index = 1
        _objs = order_filled_stat_objs.filter(
            mfr_part_number=order_good_obj.mfr_part_number
        ).order_by("-extended_price")
        for _obj in _objs:
            row_data = []
            row_data_end = [_obj.unit_price, _obj.quantity, _obj.extended_price]
            if index == 1:
                row_data = row_data_first_1 + row_data_end
            else:
                row_data = row_data_first_2 + row_data_end
            data.append(row_data)
            index += 1
    save_data_to_excel(export_path, data)


def export_by_parts(path="11_done.xlsx", parts=None, process=False):
    """
    path: 导出文件名称
    parts: list
    process: 是否加工
    """
    parts_1 = get_data_by_excel("/Users/myard/Desktop/1.xlsx", begin_row=1, cols=[3])[0]
    parts_2 = get_data_by_excel("/Users/myard/Desktop/2.xlsx", begin_row=1, cols=[6])[0]
    set_1 = set(parts_1) - set(parts_2)
    parts = list(set_1)
    parts.sort()

    data = []
    row_data = [
        "contractor_name",  # OrderGood
        "contract_number",  # OrderGood
        "manufacturer_name",  # gsa
        "mfr_part_number",  # OrderGood part
        "vendor_part_no",  # ECGood
        "item_name",  # OrderGood
        "product_description",  # gsa
        "mfr_name",  # OrderGood
        "extended_price",  # OrderGood
        "ingram_micro_price",  # ECGood
        "msrp",  # ECGood
        "federal_govt_spa",  # ECGood
        "AMAZON",  # 暂无
        "gsa_advantage_price_1",  # gsa
        "gsa_advantage_price_2",  # gsa
        "gsa_advantage_price_3",  # gsa
        "coo",  # gsa
        "url",  # gsa
        "source",  # gsa
    ]
    data.append(row_data)
    for i, part in enumerate(parts):
        if not part:
            continue
        if isinstance(part, float):
            part = str(int(part))
        row_data = []
        # 处理数据
        ec_objs = ECGood.objects.filter(part=part)
        if ec_objs:
            ec_obj = ec_objs[0]
        else:
            if process:
                continue
            else:
                ec_obj = ECGood(part=part)
        if ec_obj.federal_govt_spa == 0 and ec_obj.ingram_micro_price == 0:
            if process:
                continue
            else:
                pass
        gsa_objs = GSAGood.objects.filter(part=part)
        if (not process) and (not gsa_objs):
            gsa_obj = GSAGood(part=part)  # 没有的情况
            with open("1.txt", "a+") as f:
                f.write(f"{part}\n")
            gsa_objs = [gsa_obj]

        for gsa_obj in gsa_objs:
            _row_data = []
            _row_data.extend(row_data)
            gsa_advantage_price_2 = float(gsa_obj.gsa_advantage_price_2)
            # 判断数值是否合理
            min_price = 0
            if (
                ec_obj.federal_govt_spa
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                min_price = ec_obj.federal_govt_spa
            if (
                ec_obj.ingram_micro_price
                and 0.5 * gsa_advantage_price_2
                <= ec_obj.federal_govt_spa
                <= 1.5 * gsa_advantage_price_2
            ):
                if min_price == 0:
                    min_price = ec_obj.ingram_micro_price
                else:
                    min_price = min(min_price, ec_obj.ingram_micro_price)
            if min_price or (not process):  # 数据合理
                # 处理描述
                description = ""
                if gsa_obj.product_description:
                    description = gsa_obj.product_description
                elif gsa_obj.product_description2:
                    description = gsa_obj.product_description2
                    if gsa_obj.product_description2_strong:
                        strong = (
                            gsa_obj.product_description2_strong.split("by")[-1]
                            .strip()
                            .strip(".")
                        )
                        description = description.replace(strong, "TechFocus LLC")
                    if "For further" in description:
                        description = description.split("For further")[0]
                    description += "For further information contact TechFocus at 304-906-8124 Or email lwang@techfocusUSA.com"
                else:
                    description = ""
                order_good_obj = models.OrderGood.objects.filter(
                    mfr_part_number=part
                ).first()
                # 加数据
                _row_data.append(
                    order_good_obj.contractor_name
                )  # "contractor_name",  # OrderGood
                _row_data.append(
                    order_good_obj.contract_number
                )  # "contract_number",  # OrderGood
                _row_data.append(
                    gsa_obj.manufacturer_name
                )  # "manufacturer_name",  # gsa
                _row_data.append(part)  # "mfr_part_number",  # OrderGood part
                _row_data.append(ec_obj.vendor_part_no)  # "vendor_part_no",  # ECGood
                _row_data.append(order_good_obj.item_name)  # "item_name",  # OrderGood
                _row_data.append(description)  # "product_description",  # gsa
                _row_data.append(order_good_obj.mfr_name)  # "mfr_name",  # OrderGood
                _row_data.append(
                    order_good_obj.extended_price
                ),  # "extended_price",  # OrderGood
                _row_data.append(
                    ec_obj.ingram_micro_price
                )  # "ingram_micro_price",  # ECGood
                _row_data.append(ec_obj.msrp)  # "msrp",  # ECGood
                _row_data.append(
                    ec_obj.federal_govt_spa
                )  # "federal_govt_spa",  # ECGood
                _row_data.append("")  # "AMAZON",  # 暂无
                _row_data.append(gsa_obj.gsa_advantage_price_1)
                _row_data.append(gsa_obj.gsa_advantage_price_2)
                _row_data.append(gsa_obj.gsa_advantage_price_3)
                _row_data.append(gsa_obj.coo)
                _row_data.append(gsa_obj.url)
                _row_data.append(gsa_obj.source)
                data.append(_row_data)

    save_data_to_excel(path, data)


if __name__ == "__main__":
    pass
    # spider()
    # export("", 3, 0, 6, 1, True)
    # export("", 3, 0, 6, 1, False)
    # import_order_filled("/Users/myard/Desktop/1.xlsx", 1, 0, 8)
    # export_stat()
    # export_by_parts()
