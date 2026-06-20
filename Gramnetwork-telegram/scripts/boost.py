import asyncio
import random

from colorama import Fore, Style

from scripts.common import (
    BOOST_COOLDOWN_SECONDS,
    GramClient,
    account_label,
    print_border,
    run_accounts,
)

MAX_ENERGY = 100
DEFAULT_ENERGY_BOOST = 10
DEFAULT_POWER_BOOST = 5.0
AD_WATCH_MIN_SECONDS = 30
AD_WATCH_MAX_SECONDS = 60


def _msg(language: str, key: str) -> str:
    messages = {
        "vi": {
            "title": "TỰ ĐỘNG BOOST",
            "blocked": "Tài khoản bị khóa",
            "maintenance": "Hệ thống đang bảo trì",
            "new_miner": "Tài khoản chưa đăng ký — mở mini app trong Telegram để đăng ký trước",
            "mining_power": "Công suất đào",
            "active_boost": "Boost đang hoạt động",
            "energy": "Năng lượng",
            "energy_boost": "Energy Boost",
            "power_boost": "Power Boost",
            "cooldown": "Thời gian chờ",
            "ready": "Sẵn sàng",
            "full": "Đầy",
            "waiting_ad": "Đang xem quảng cáo",
            "energy_boosting": "Đang kích hoạt Energy Boost",
            "power_boosting": "Đang kích hoạt Power Boost",
            "done": "Hoàn tất",
            "fail": "Thất bại",
            "unavailable": "Chưa sẵn sàng boost",
            "next_check": "Kiểm tra boost tiếp theo",
        },
        "en": {
            "title": "AUTOMATIC BOOST",
            "blocked": "Account is blocked",
            "maintenance": "System is under maintenance",
            "new_miner": "Account not registered — open the mini app in Telegram first",
            "mining_power": "Mining power",
            "active_boost": "Active boost",
            "energy": "Energy",
            "energy_boost": "Energy Boost",
            "power_boost": "Power Boost",
            "cooldown": "Cooldown",
            "ready": "Ready",
            "full": "Full",
            "waiting_ad": "Watching ad",
            "energy_boosting": "Activating Energy Boost",
            "power_boosting": "Activating Power Boost",
            "done": "Done",
            "fail": "Failed",
            "unavailable": "Boost not available yet",
            "next_check": "Next boost check",
        },
    }
    return messages[language][key]


def _parse_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_cooldown(seconds: int) -> str:
    seconds = max(0, seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _energy_state(user: dict) -> dict:
    energy = _parse_int(user.get("energy"))
    boost_amount = _parse_int(user.get("energy_boost_amount"), DEFAULT_ENERGY_BOOST)
    cooldown = _parse_int(user.get("energy_boost_time_left"))
    return {
        "energy": energy,
        "boost_amount": boost_amount,
        "cooldown": cooldown,
        "is_full": energy >= MAX_ENERGY,
        "can_boost": energy < MAX_ENERGY and cooldown <= 0,
    }


def _power_boost_state(tasks_data: dict) -> dict:
    time_left_ms = _parse_int(tasks_data.get("boost_time_left"))
    amount = _parse_float(tasks_data.get("boost_amount"), DEFAULT_POWER_BOOST)
    cooldown = max(0, time_left_ms // 1000)
    return {
        "amount": amount,
        "cooldown": cooldown,
        "can_boost": cooldown <= 0,
    }


def _show_boost_info(user: dict, power_boost: dict, language: str):
    energy = _energy_state(user)
    m = lambda k: _msg(language, k)

    print(
        f"{Fore.CYAN}│ {m('mining_power')}: "
        f"{Fore.GREEN}{user.get('mining_power', '-')} GH/s{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}│ {m('active_boost')}: "
        f"{Fore.GREEN}+{power_boost['amount']} GH/s & +0.10 GRM{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}│ {m('energy')}: "
        f"{Fore.YELLOW}{energy['energy']}/{MAX_ENERGY}{Style.RESET_ALL}"
    )

    if energy["is_full"]:
        energy_status = m("full")
    elif energy["cooldown"] > 0:
        energy_status = _format_cooldown(energy["cooldown"])
    else:
        energy_status = m("ready")
    print(
        f"{Fore.CYAN}│ {m('energy_boost')} (+{energy['boost_amount']}): "
        f"{Fore.YELLOW}{energy_status}{Style.RESET_ALL}"
    )

    if power_boost["can_boost"]:
        power_status = m("ready")
        color = Fore.GREEN
    else:
        power_status = _format_cooldown(power_boost["cooldown"])
        color = Fore.YELLOW
    print(
        f"{Fore.CYAN}│ {m('power_boost')} (+{power_boost['amount']} GH/s): "
        f"{color}{power_status}{Style.RESET_ALL}"
    )


async def _simulate_ad_watch(language: str):
    wait_seconds = random.randint(AD_WATCH_MIN_SECONDS, AD_WATCH_MAX_SECONDS)
    print(
        f"{Fore.YELLOW}⏳ {_msg(language, 'waiting_ad')} "
        f"({wait_seconds}s){Style.RESET_ALL}"
    )
    await asyncio.sleep(wait_seconds)


async def _apply_energy_boost(client: GramClient, language: str) -> tuple[bool, dict]:
    print(f"{Fore.CYAN}→ {_msg(language, 'energy_boosting')}{Style.RESET_ALL}")
    result = await client.boost_energy()
    if result.get("success"):
        print(f"{Fore.GREEN}✅ {_msg(language, 'energy_boosting')}: {_msg(language, 'done')}{Style.RESET_ALL}")
        if result.get("message"):
            print(f"{Fore.GREEN}   {result['message']}{Style.RESET_ALL}")
        user = (await client.get_user_data()).get("user") or {}
        return True, user

    print(
        f"{Fore.RED}❌ {_msg(language, 'energy_boosting')}: {_msg(language, 'fail')} — "
        f"{result.get('message', '')}{Style.RESET_ALL}"
    )
    return False, {}


async def _apply_power_boost(client: GramClient, language: str) -> bool:
    print(f"{Fore.CYAN}→ {_msg(language, 'power_boosting')}{Style.RESET_ALL}")
    result = await client.boost_power()
    if result.get("success"):
        print(f"{Fore.GREEN}✅ {_msg(language, 'power_boosting')}: {_msg(language, 'done')}{Style.RESET_ALL}")
        if result.get("message"):
            print(f"{Fore.GREEN}   {result['message']}{Style.RESET_ALL}")
        return True

    print(
        f"{Fore.RED}❌ {_msg(language, 'power_boosting')}: {_msg(language, 'fail')} — "
        f"{result.get('message', '')}{Style.RESET_ALL}"
    )
    return False


async def _fetch_power_boost(client: GramClient) -> dict:
    data = await client.get_tasks()
    if not data.get("success"):
        return _power_boost_state({})
    return _power_boost_state(data)


def _next_boost_wait(energy: dict, power: dict) -> int:
    waits = []
    if energy["cooldown"] > 0:
        waits.append(energy["cooldown"])
    if power["cooldown"] > 0:
        waits.append(power["cooldown"])
    if waits:
        return min(waits) + 1
    if not energy["can_boost"] and not power["can_boost"]:
        return BOOST_COOLDOWN_SECONDS
    return BOOST_COOLDOWN_SECONDS


async def ensure_energy(
    client: GramClient,
    user: dict,
    language: str,
    min_energy: int = 1,
) -> tuple[bool, dict]:
    user = user or {}

    while _parse_int(user.get("energy")) < min_energy:
        state = _energy_state(user)
        if state["is_full"]:
            break
        if not state["can_boost"]:
            if state["cooldown"] > 0:
                print(
                    f"{Fore.YELLOW}⏳ {_msg(language, 'cooldown')} "
                    f"({_format_cooldown(state['cooldown'])}){Style.RESET_ALL}"
                )
                await asyncio.sleep(state["cooldown"] + 1)
                user = (await client.get_user_data()).get("user") or {}
                continue
            break

        await _simulate_ad_watch(language)
        success, user = await _apply_energy_boost(client, language)
        if not success:
            break

    return _parse_int(user.get("energy")) >= min_energy, user


async def _boost_loop(client: GramClient, language: str):
    while True:
        data = await client.get_user_data()
        user = data.get("user") or {}
        power_boost = await _fetch_power_boost(client)
        energy = _energy_state(user)
        _show_boost_info(user, power_boost, language)

        boosted = False

        if energy["can_boost"]:
            await _simulate_ad_watch(language)
            success, user = await _apply_energy_boost(client, language)
            boosted = boosted or success
            energy = _energy_state(user)

        if power_boost["can_boost"]:
            await _simulate_ad_watch(language)
            if await _apply_power_boost(client, language):
                boosted = True
                power_boost = await _fetch_power_boost(client)

        if not boosted:
            print(f"{Fore.YELLOW}ℹ {_msg(language, 'unavailable')}{Style.RESET_ALL}")

        user = (await client.get_user_data()).get("user") or {}
        power_boost = await _fetch_power_boost(client)
        energy = _energy_state(user)
        wait = _next_boost_wait(energy, power_boost)
        print(
            f"{Fore.YELLOW}⏳ {_msg(language, 'next_check')} "
            f"in {_format_cooldown(wait)} ({wait}s){Style.RESET_ALL}"
        )
        await asyncio.sleep(wait)


async def process_account(index: int, init_data: str, proxy, language: str):
    label = account_label(init_data)
    print_border(f"#{index + 1} {label}", Fore.MAGENTA)

    async with GramClient(init_data, proxy) as client:
        data = await client.get_user_data()

        if data.get("settings", {}).get("maintenance") == "on":
            print(f"{Fore.RED}❌ {_msg(language, 'maintenance')}{Style.RESET_ALL}\n")
            return

        user = data.get("user") or {}
        if user.get("status") == "block":
            print(f"{Fore.RED}❌ {_msg(language, 'blocked')}{Style.RESET_ALL}\n")
            return

        if not data.get("success") or user.get("username") == "New Miner":
            print(f"{Fore.RED}❌ {_msg(language, 'new_miner')}{Style.RESET_ALL}")
            if data.get("message"):
                print(f"{Fore.YELLOW}   {data['message']}{Style.RESET_ALL}\n")
            return

        await _boost_loop(client, language)


async def run_boost(language: str):
    print_border(_msg(language, "title"), Fore.GREEN)
    await run_accounts(process_account, language)
