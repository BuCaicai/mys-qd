import os
import re
import time
import json
import uuid
import qrcode
import requests
from config import logger, config, TEMP_PATH, COOKIE_PATH


def HELP():
    print("\n请选择要执行的函数：")
    print("1. 登录")
    print("2. 签到")
    print("3. 退出")


#####################
# 公共
#####################
def get_cookie():
    with open(COOKIE_PATH, 'r', encoding='utf-8') as f:
        res = json.load(f)
    return res


def get_game_info(game, cookie):
    game = f"{game}_cn"
    url = f"https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz={game}"
    headers = {
        "Cookie": cookie
    }
    response = requests.get(url=url, headers=headers)
    res = response.json()
    logger.debug(f"获取游戏信息返回值: {res}")
    game_uid = res['data']['list'][0]['game_uid']
    region = res['data']['list'][0]['region']
    return game_uid, region


#####################
# 登录
#####################
APP_VERSION = "2.71.1"
DEVICE_NAME = "Xiaomi MI 6"
DEVICE_MODEL = "MI 6"
DEVICE_ID = uuid.uuid4().hex

HEADERS_QRCODE_API = {
    "x-rpc-app_version": APP_VERSION,
    "DS": None,
    "x-rpc-aigis": "",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "x-rpc-game_biz": "bbs_cn",
    "x-rpc-sys_version": "12",
    "x-rpc-device_id": DEVICE_ID,
    "x-rpc-device_name": DEVICE_NAME,
    "x-rpc-device_model": DEVICE_MODEL,
    "x-rpc-app_id": "bll8iq97cem8",
    "x-rpc-client_type": "4",
    "User-Agent": "okhttp/4.9.3",
}


def get_qr_code():
    """
    获取登录url和id
    :return:
    """
    url = "https://passport-api.miyoushe.com/account/ma-cn-passport/web/createQRLogin"
    response = requests.post(url, headers=HEADERS_QRCODE_API)
    data = response.json()
    logger.debug(f"获取登录二维码返回体: {data}")
    qr_code_url = data["data"]["url"]
    ticket = data["data"]["ticket"]
    return qr_code_url, ticket


def show_qrcode(url: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    qr_path = os.path.join(TEMP_PATH, 'code.png')
    img.save(qr_path)
    logger.info(f"登录二维码保存到: {qr_path}")


def check_login_status(ticket):
    """
    检测登录状态
    """
    url = 'https://passport-api.miyoushe.com/account/ma-cn-passport/web/queryQRLoginStatus'
    data = {
        "ticket": ticket
    }

    num = 0
    while True:
        response = requests.post(url, json=data, headers=HEADERS_QRCODE_API)
        res = response.json()

        logger.debug(res)

        if res['retcode'] == 0:
            if res['data']['status'] == "Created":
                logger.info("还没有扫描二维码，请尽快扫描...")
            elif res['data']['status'] == "Confirmed":
                uid = res['data']['user_info']['aid']
                mid = res['data']['user_info']['mid']
                config.set('mys', 'uid', uid)
                config.set('mys', 'mid', mid)
                with open('config.cfg', 'w', encoding='utf-8') as f:
                    config.write(f)
                headers_dict = dict(response.headers)
                logger.info(f"登录成功。")
                return headers_dict
        else:
            logger.error(f"Failed to check login status: {res['message']}")
            return None

        num += 1
        if num >= 30:
            logger.error("超时，请重新登录。")
            return None
        time.sleep(2)


def check_qr_login(ticket):
    logger.debug("检查登录状态...")
    cookie_dict = {}
    cookie_headers = check_login_status(ticket)
    set_cookie = cookie_headers.get('Set-Cookie', '')
    logger.debug(f"cookie返回值: {set_cookie}")
    cookie_names = ['account_id', 'ltoken', 'ltuid', 'cookie_token', 'account_mid_v2']
    for name in cookie_names:
        match = re.search(rf'{name}=([^;]+)', set_cookie)
        if match:
            cookie_dict[name] = match.group(1)

    if not cookie_dict:
        logger.error(f"获取cookie失败.")
    else:
        with open(COOKIE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cookie_dict, f, ensure_ascii=False, indent=4)
        logger.info(f"cookie已保存: {COOKIE_PATH}")


def login():
    qr_code_url, ticket = get_qr_code()
    show_qrcode(qr_code_url)
    logger.info("请使用米游社扫码登陆。")
    check_qr_login(ticket)


#####################
# 签到
#####################
QD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; Unspecified Device) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-rpc-device_model": "MI 6",
    "Referer": "https://webstatic.miyoushe.com/",
    "x-rpc-device_name": "Xiaomi MI 6",
    "Origin": "https://webstatic.miyoushe.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Site": "same-site",
    "x-rpc-device_fp": "38d7cd029d992",
    "x-rpc-channel": "xiaomi",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "x-rpc-app_version": "2.71.1",
    "x-rpc-client_type": "1",
    "x-rpc-verify_key": "bll8iq97cem8",
    "x-rpc-device_id": "16fc6535bc794b8fae8440bf9415ec1d",
    "Content-Type": "application/json; charset=utf-8",
    "x-rpc-sys_version": "12",
    "Sec-Fetch-Mode": "cors",
    'x-rpc-signgame': "",
    "Cookie": ""
}


def qd_request(game):
    cookie_dict = get_cookie()
    cookie_str = ';'.join(f"{k}={v}" for k, v in cookie_dict.items())
    category = config['yx'][f'{game}-dh']
    game_uid, region = get_game_info(category, cookie_str)
    config.set('yx', f'{game}_uid', game_uid)
    config.set('yx', f'{game}-region', region)
    with open('config.cfg', 'w', encoding='utf-8') as f:
        config.write(f)

    if game == "zzz":
        url = config['api']['qd_url-zzz']
        QD_HEADERS['x-rpc-signgame'] = "zzz"
    else:
        url = config['api']['qd_url']
        QD_HEADERS['x-rpc-signgame'] = category

    QD_HEADERS['Cookie'] = cookie_str
    data = {
        "act_id": config['yx'][f'{game}-hdid'],
        "region": region,
        "uid": game_uid,
        "lang": "zh-cn"
    }

    response = requests.post(url, headers=QD_HEADERS, json=data)
    data = response.json()
    logger.debug(f"签到返回体: {data}")
    logger.info(f"游戏 {game} 签到状态: {data['message']}")


def yx_sign():
    print("\n请选择要游戏类别：")
    print("1. 原神")
    print("2. 星穹轨道")
    print("3. 绝区零")
    choice = input("请输入你的选择: ")
    if choice == "1":
        qd_request('ys')
    elif choice == "2":
        qd_request('xqgd')
    elif choice == "3":
        qd_request('zzz')
    else:
        print("无效的选择。")


#####################
# 主程序
#####################
def main():
    while True:
        HELP()

        choice = input("请输入你的选择: ")
        if choice == "1":
            login()
        elif choice == "2":
            yx_sign()
        elif choice == "3":
            print("退出程序")
            break
        else:
            print("无效的选择，请重新输入。")


if __name__ == '__main__':
    main()
