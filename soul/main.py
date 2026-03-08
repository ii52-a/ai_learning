from __future__ import annotations

from soul.core.orchestrator import SoulCore


def _format_status(core: SoulCore) -> str:
    status = core.get_status()
    heartbeat = status["heartbeat"]
    return (
        f"{status['name']} 当前状态正常。"
        f" 情绪: {status['emotion']}。"
        f" 心跳: {heartbeat.bpm} BPM。"
        f" 已运行 {heartbeat.uptime_seconds:.0f} 秒。"
        f" 当前模型: {core.current_model_summary()}。"
    )


def _format_models(core: SoulCore) -> str:
    models = core.list_models()
    if not models:
        return "当前没有可用模型。"
    items = [f"{item['alias']} -> {item['provider']} / {item['model']}" for item in models]
    return "可用模型: " + "；".join(items)


def _format_screen(core: SoulCore) -> str:
    snapshot = core.inspect_screen()
    active_window = snapshot.get("active_window") or "未知"
    visible_windows = snapshot.get("visible_windows") or []
    screen_size = snapshot.get("screen_size") or (0, 0)
    ocr_excerpt = snapshot.get("ocr_excerpt") or "未提取到文字"
    preview = " | ".join(visible_windows[:5]) if visible_windows else "无"
    return (
        f"我刚看了一眼屏幕。当前活动窗口是《{active_window}》，"
        f"分辨率 {screen_size[0]}x{screen_size[1]}，"
        f"可见窗口有: {preview}。OCR 摘要: {ocr_excerpt}"
    )


def _format_windows(core: SoulCore) -> str:
    windows = core.list_windows()
    if not windows:
        return "当前没有枚举到可见窗口。"
    return "当前可见窗口有: " + " | ".join(windows[:10])


def _format_tasks(core: SoulCore, pending_only: bool = False) -> str:
    tasks = core.incomplete_tasks() if pending_only else core.recent_tasks()
    if not tasks:
        return "当前没有任务记录。"
    items = []
    for task in tasks[:5]:
        goal = task.get("goal", "未命名任务")
        steps = task.get("steps", [])
        statuses = [step.get("status", "pending") for step in steps]
        items.append(f"{goal} [{', '.join(statuses[:4])}]")
    return ("未完成任务: " if pending_only else "最近任务: ") + "；".join(items)


def main() -> None:
    core = SoulCore.build_default()
    print(
        "多伦娜已启动。输入 /exit 退出，/status 查看状态，/memory 查看重要记忆，"
        "/models 查看模型，/model <alias> 切换模型，/screen 看屏幕，"
        "/window 或 /windows 看窗口，/processes 看进程，/tasks 看最近任务，"
        "/pending 看未完成任务，/desktop <目标> 启动桌面 autopilot。"
    )
    try:
        while True:
            user_input = input("you> ").strip()
            if not user_input:
                continue
            if user_input in {"/exit", "/quit"}:
                break
            if user_input == "/status":
                print(f"{core.name}> {_format_status(core)}")
                continue
            if user_input == "/memory":
                print(f"{core.name}> {core.memory.important_event_summaries()}")
                continue
            if user_input == "/models":
                print(f"{core.name}> {_format_models(core)}")
                continue
            if user_input.startswith("/model "):
                alias = user_input.split(maxsplit=1)[1].strip()
                message = f"模型已切换到 {alias}。" if core.switch_model(alias) else f"没有这个模型别名: {alias}"
                print(f"{core.name}> {message}")
                continue
            if user_input == "/screen":
                print(f"{core.name}> {_format_screen(core)}")
                continue
            if user_input in {"/window", "/windows"}:
                print(f"{core.name}> {_format_windows(core)}")
                continue
            if user_input == "/processes":
                print(f"{core.name}> {core.list_processes()}")
                continue
            if user_input == "/tasks":
                print(f"{core.name}> {_format_tasks(core)}")
                continue
            if user_input == "/pending":
                print(f"{core.name}> {_format_tasks(core, pending_only=True)}")
                continue
            if user_input.startswith("/desktop "):
                goal = user_input.split(maxsplit=1)[1].strip()
                print(f"{core.name}> {core.run_desktop_goal(goal)}")
                continue
            print(f"{core.name}> {core.step(user_input)}")
    finally:
        core.stop()


if __name__ == "__main__":
    main()
