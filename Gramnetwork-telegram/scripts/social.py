import asyncio

from colorama import Fore, Style

from scripts.common import (
    TASK_CHECK_INTERVAL_SECONDS,
    GramClient,
    account_label,
    print_border,
    run_accounts,
)

TELEGRAM_TASK_TYPES = {"telegram_chat", "telegram_bot"}
TELEGRAM_WAIT_SECONDS = 2
DEFAULT_TASK_WAIT_SECONDS = 30


def _msg(language: str, key: str) -> str:
    messages = {
        "vi": {
            "title": "TỰ ĐỘNG LÀM NHIỆM VỤ",
            "unauthorized": "initData không hợp lệ hoặc tài khoản chưa đăng ký",
            "blocked": "Tài khoản bị khóa",
            "maintenance": "Hệ thống đang bảo trì",
            "new_miner": "Tài khoản chưa đăng ký — mở mini app trong Telegram để đăng ký trước",
            "no_tasks": "Không có nhiệm vụ nào",
            "all_done": "Tất cả nhiệm vụ đã hoàn thành",
            "running": "Đang làm nhiệm vụ",
            "waiting": "Đang chờ xác minh",
            "success": "Hoàn thành",
            "fail": "Thất bại",
            "reward": "Thưởng",
            "next_check": "Kiểm tra nhiệm vụ tiếp theo",
        },
        "en": {
            "title": "AUTOMATIC TASK COMPLETION",
            "unauthorized": "Invalid initData or account not registered",
            "blocked": "Account is blocked",
            "maintenance": "System is under maintenance",
            "new_miner": "Account not registered — open the mini app in Telegram first",
            "no_tasks": "No tasks available",
            "all_done": "All tasks already completed",
            "running": "Running task",
            "waiting": "Waiting for verification",
            "success": "Completed",
            "fail": "Failed",
            "reward": "Reward",
            "next_check": "Next task check",
        },
    }
    return messages[language][key]


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d} ({seconds}s)"


async def _complete_task(client: GramClient, task: dict, language: str) -> bool:
    task_type = str(task.get("type", "")).lower()
    wait_seconds = TELEGRAM_WAIT_SECONDS if task_type in TELEGRAM_TASK_TYPES else DEFAULT_TASK_WAIT_SECONDS

    print(
        f"{Fore.YELLOW}⏳ {_msg(language, 'waiting')} "
        f"({wait_seconds}s): {task.get('title', task.get('id'))}{Style.RESET_ALL}"
    )
    await asyncio.sleep(wait_seconds)

    result = await client.complete_task(int(task["id"]))
    if result.get("success"):
        reward = result.get("reward", task.get("reward", "?"))
        print(f"{Fore.GREEN}✅ {_msg(language, 'success')}: {task.get('title')} (+{reward} GRM){Style.RESET_ALL}")
        return True

    print(
        f"{Fore.RED}❌ {_msg(language, 'fail')}: {task.get('title')} — "
        f"{result.get('message', '')}{Style.RESET_ALL}"
    )
    return False


async def _run_pending_tasks(client: GramClient, language: str) -> int:
    data = await client.get_tasks()
    if not data.get("success"):
        print(f"{Fore.RED}❌ {data.get('message', _msg(language, 'unauthorized'))}{Style.RESET_ALL}")
        return 0

    tasks = data.get("tasks") or []
    pending = [t for t in tasks if not t.get("is_completed")]

    if not tasks:
        print(f"{Fore.YELLOW}ℹ {_msg(language, 'no_tasks')}{Style.RESET_ALL}")
        return 0

    if not pending:
        print(f"{Fore.GREEN}✅ {_msg(language, 'all_done')}{Style.RESET_ALL}")
        return 0

    completed = 0
    for task in pending:
        print(
            f"{Fore.CYAN}→ {_msg(language, 'running')}: "
            f"{task.get('title')} (+{task.get('reward')} GRM){Style.RESET_ALL}"
        )
        if await _complete_task(client, task, language):
            completed += 1

    print(f"{Fore.GREEN}│ {_msg(language, 'success')}: {completed}/{len(pending)}{Style.RESET_ALL}")
    return completed


async def _task_loop(client: GramClient, language: str):
    while True:
        await _run_pending_tasks(client, language)
        print(
            f"{Fore.YELLOW}⏳ {_msg(language, 'next_check')} "
            f"in {_format_duration(TASK_CHECK_INTERVAL_SECONDS)}{Style.RESET_ALL}"
        )
        await asyncio.sleep(TASK_CHECK_INTERVAL_SECONDS)


async def process_account(index: int, init_data: str, proxy, language: str):
    label = account_label(init_data)
    print_border(f"#{index + 1} {label}", Fore.MAGENTA)

    async with GramClient(init_data, proxy) as client:
        profile = await client.get_user_data()

        if profile.get("settings", {}).get("maintenance") == "on":
            print(f"{Fore.RED}❌ {_msg(language, 'maintenance')}{Style.RESET_ALL}\n")
            return

        user = profile.get("user") or {}
        if user.get("status") == "block":
            print(f"{Fore.RED}❌ {_msg(language, 'blocked')}{Style.RESET_ALL}\n")
            return

        if not profile.get("success") or user.get("username") == "New Miner":
            print(f"{Fore.RED}❌ {_msg(language, 'new_miner')}{Style.RESET_ALL}")
            if profile.get("message"):
                print(f"{Fore.YELLOW}   {profile['message']}{Style.RESET_ALL}\n")
            return

        await _task_loop(client, language)

    print("")


async def run_social(language: str):
    print_border(_msg(language, "title"), Fore.GREEN)
    await run_accounts(process_account, language)
