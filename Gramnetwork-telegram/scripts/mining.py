import asyncio

from colorama import Fore, Style

from scripts.common import (
    MINING_SESSION_SECONDS,
    POLL_INTERVAL_SECONDS,
    GramClient,
    account_label,
    print_border,
    run_accounts,
)

SESSION_END_BUFFER = 5
CLAIM_TO_START_DELAY = 2


def _msg(language: str, key: str) -> str:
    messages = {
        "vi": {
            "title": "TỰ ĐỘNG ĐÀO $GRM",
            "blocked": "Tài khoản bị khóa",
            "maintenance": "Hệ thống đang bảo trì",
            "new_miner": "Tài khoản chưa đăng ký — mở mini app trong Telegram để đăng ký trước",
            "status": "Trạng thái",
            "rate": "Tốc độ đào",
            "power": "Công suất",
            "time_left": "Thời gian còn lại",
            "earned": "Token đã đào",
            "energy": "Năng lượng",
            "balance": "Số dư",
            "start": "Bắt đầu đào",
            "claim": "Nhận token đào",
            "daily_claim": "Nhận thưởng ngày",
            "session_active": "Phiên sẵn sàng nhận — đang claim",
            "session_inactive": "Phiên không hoạt động — đang bắt đầu đào",
            "session_mining": "Đang đào, chờ phiên kết thúc",
            "low_energy": "Năng lượng thấp — đang boost trước khi đào",
            "done": "Hoàn tất",
            "fail": "Thất bại",
        },
        "en": {
            "title": "AUTOMATIC $GRM MINING",
            "blocked": "Account is blocked",
            "maintenance": "System is under maintenance",
            "new_miner": "Account not registered — open the mini app in Telegram first",
            "status": "Status",
            "rate": "Mining rate",
            "power": "Mining power",
            "time_left": "Time left",
            "earned": "Tokens earned",
            "energy": "Energy",
            "balance": "Balance",
            "start": "Start mining",
            "claim": "Claim mined tokens",
            "daily_claim": "Claim daily reward",
            "session_active": "Session active — claiming",
            "session_inactive": "Session inactive — starting mining",
            "session_mining": "Session mining — waiting to finish",
            "low_energy": "Low energy — boosting before mining",
            "done": "Done",
            "fail": "Failed",
        },
    }
    return messages[language][key]


def _mining_status(user: dict) -> str:
    return str(user.get("mining_status", "")).lower()


def _parse_time_left(value) -> int:
    if not value:
        return 0
    text = str(value).strip().lower()
    if text in {"ready", "00:00:00", "-"}:
        return 0
    parts = text.split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (int(p) for p in parts)
    except ValueError:
        return 0
    return hours * 3600 + minutes * 60 + seconds


def _session_is_mining(user: dict) -> bool:
    status = _mining_status(user)
    if "inactive" in status or "ready to claim" in status or "ready to start" in status:
        return False
    time_left = _parse_time_left(user.get("time_left"))
    return time_left > 0 and ("active" in status or "mining" in status)


def _session_is_active(user: dict) -> bool:
    """Active = session finished, Claim button is available."""
    status = _mining_status(user)
    if "inactive" in status:
        return False
    time_left = _parse_time_left(user.get("time_left"))
    if "ready to claim" in status or "completed" in status:
        return True
    return ("active" in status or "mining" in status) and time_left == 0


def _session_is_inactive(user: dict) -> bool:
    """Inactive = no session running, Start Mining button is available."""
    if _session_is_mining(user) or _session_is_active(user):
        return False
    status = _mining_status(user)
    return (
        "inactive" in status
        or "ready to start" in status
        or "start" in status
        or status in {"", "idle", "stopped"}
    )


def _show_user_info(user: dict, language: str):
    m = lambda k: _msg(language, k)
    print(f"{Fore.CYAN}│ {m('status')}: {Fore.YELLOW}{user.get('mining_status', '-')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {m('rate')}: {Fore.GREEN}{user.get('mining_rate', '-')} GRM/h{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {m('power')}: {Fore.GREEN}{user.get('mining_power', '-')} GH/s{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {m('time_left')}: {Fore.YELLOW}{user.get('time_left', '-')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {m('earned')}: {Fore.GREEN}{user.get('tokens_earned', '-')} GRM{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {m('energy')}: {Fore.YELLOW}{user.get('energy', '-')}/100{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│ {m('balance')}: {Fore.GREEN}{user.get('total_balance', '-')} GRM{Style.RESET_ALL}")


async def _refresh_user(client: GramClient) -> dict:
    data = await client.get_user_data()
    return data.get("user") or {}


async def _claim_session(client: GramClient, language: str) -> bool:
    result = await client.claim_mining()
    if result.get("success"):
        print(f"{Fore.GREEN}✅ {_msg(language, 'claim')}: {_msg(language, 'done')}{Style.RESET_ALL}")
        return True
    print(f"{Fore.RED}❌ {_msg(language, 'claim')}: {_msg(language, 'fail')} — {result.get('message', '')}{Style.RESET_ALL}")
    return False


async def _start_session(client: GramClient, user: dict, language: str) -> bool:
    try:
        energy = int(user.get("energy") or 0)
    except (TypeError, ValueError):
        energy = 0

    if energy <= 0:
        print(f"{Fore.CYAN}→ {_msg(language, 'low_energy')}{Style.RESET_ALL}")
        from scripts.boost import ensure_energy

        ready, user = await ensure_energy(client, user, language)
        if not ready:
            print(
                f"{Fore.RED}❌ {_msg(language, 'start')}: {_msg(language, 'fail')} — "
                f"insufficient energy{Style.RESET_ALL}"
            )
            return False
        _show_user_info(user, language)

    result = await client.start_mining()
    if result.get("success"):
        print(f"{Fore.GREEN}✅ {_msg(language, 'start')}: {_msg(language, 'done')}{Style.RESET_ALL}")
        return True
    print(f"{Fore.RED}❌ {_msg(language, 'start')}: {_msg(language, 'fail')} — {result.get('message', '')}{Style.RESET_ALL}")
    return False


async def _try_daily_claim(client: GramClient, user: dict, language: str):
    claim_in = str(user.get("claim_in", "")).lower()
    if claim_in not in ("ready", "00:00:00", ""):
        return

    daily = await client.claim_daily()
    if daily.get("success"):
        print(f"{Fore.GREEN}✅ {_msg(language, 'daily_claim')}: {_msg(language, 'done')}{Style.RESET_ALL}")
    elif daily.get("message"):
        print(f"{Fore.YELLOW}ℹ {_msg(language, 'daily_claim')}: {daily['message']}{Style.RESET_ALL}")


async def _sleep_while_mining(user: dict, language: str):
    time_left = _parse_time_left(user.get("time_left"))
    if time_left <= 0:
        time_left = MINING_SESSION_SECONDS
    wait = min(time_left, MINING_SESSION_SECONDS) + SESSION_END_BUFFER
    print(
        f"{Fore.YELLOW}⏳ {_msg(language, 'session_mining')} "
        f"({_format_duration(wait)}){Style.RESET_ALL}"
    )
    await asyncio.sleep(wait)


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d} ({seconds}s)"


async def _mining_loop(client: GramClient, language: str):
    while True:
        user = await _refresh_user(client)
        _show_user_info(user, language)

        if _session_is_mining(user):
            await _sleep_while_mining(user, language)
            continue

        if _session_is_active(user):
            print(f"{Fore.CYAN}→ {_msg(language, 'session_active')}{Style.RESET_ALL}")
            await _claim_session(client, language)
            await asyncio.sleep(CLAIM_TO_START_DELAY)
            user = await _refresh_user(client)
            _show_user_info(user, language)

        if _session_is_inactive(user):
            print(f"{Fore.CYAN}→ {_msg(language, 'session_inactive')}{Style.RESET_ALL}")
            if await _start_session(client, user, language):
                user = await _refresh_user(client)
                _show_user_info(user, language)
                await _try_daily_claim(client, user, language)

        if _session_is_mining(user):
            await _sleep_while_mining(user, language)
        else:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


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

        await _mining_loop(client, language)


async def run_mining(language: str):
    print_border(_msg(language, "title"), Fore.GREEN)
    await run_accounts(process_account, language)
