"""Interactive capacity agent, Phase 1B. / Phase 1B 交互式容量 Agent。"""

import argparse
import getpass
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def configure():
    """Local interactive setup; never echo or overwrite credentials. / 本地交互配置，不回显或覆盖凭据。"""
    target = ROOT / ".env"
    if target.exists():
        print(".env already exists; edit it locally. / .env 已存在，请在本地编辑。")
        return 1
    provider = (
        input("Provider [openrouter] / 服务（回车使用 OpenRouter）: ").strip().lower()
        or "openrouter"
    )
    model = input(
        "Model ID [openrouter/free for OpenRouter] / 模型（OpenRouter 可直接回车）: "
    ).strip()
    if provider == "openrouter" and not model:
        model = "openrouter/free"
    key = getpass.getpass("API key (hidden) / API Key（隐藏输入）: ").strip()
    if not model or not key or any(c in model + key for c in "\r\n\x00\"'"):
        print("Invalid configuration. / 配置无效。")
        return 1
    from agent.llm_client import ConfigurationError, Settings

    try:
        Settings.load(
            root=ROOT,
            environ={"LLM_API_KEY": key, "LLM_MODEL": model, "LLM_PROVIDER": provider},
        )
    except ConfigurationError as exc:
        print(str(exc))
        return 1
    with target.open("x", encoding="utf-8") as handle:
        handle.write(
            f'LLM_PROVIDER={provider}\nLLM_MODEL="{model}"\nLLM_API_KEY="{key}"\nLLM_ALLOW_PAID_MODELS=false\n'
        )
    print("Saved local .env. Do not upload it. / 已保存本地 .env，请勿上传。")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="GPU capacity agent / GPU 容量规划 Agent"
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--question", help="One natural-language question / 单次自然语言问题"
    )
    modes.add_argument(
        "--demo",
        nargs="?",
        const="baseline",
        choices=["baseline", "custom", "comparison", "sensitivity", "unsupported"],
        help="Scripted offline demo, no LLM / 预设离线演示，不调用 LLM",
    )
    modes.add_argument(
        "--configure",
        action="store_true",
        help="Configure local API key interactively / 交互配置本地 API Key",
    )
    modes.add_argument(
        "--check-config",
        action="store_true",
        help="Check local configuration without a network call / 离线检查配置",
    )
    parser.add_argument(
        "--json", action="store_true", help="Full structured result / 完整结构化结果"
    )
    args = parser.parse_args(argv)
    # Ensure Chinese text is readable in Windows terminals and redirected output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    client = None
    try:
        from agent.agent import CapacityAgent
        from agent.llm_client import ConfigurationError, OpenAIClient, Settings
        from agent.presentation import format_turn

        if args.configure:
            return configure()
        if args.demo:
            from agent.demo import QUESTIONS, DemoClient

            print(
                "OFFLINE SCRIPTED DEMO — no LLM or API call. / 预设离线演示，不调用 LLM 或 API。",
                file=sys.stderr,
            )
            agent = CapacityAgent(DemoClient(args.demo))
            question = QUESTIONS[args.demo]
        else:
            try:
                settings = Settings.load()
            except ConfigurationError as exc:
                print(str(exc), file=sys.stderr)
                print(
                    "Run --configure to set up, or --demo for an offline example. / 使用 --configure 配置，或 --demo 查看离线示例。",
                    file=sys.stderr,
                )
                return 2
            if args.check_config:
                print(
                    "Local configuration is valid; API access has not been tested. / 本地配置有效，尚未验证 API 访问。"
                )
                return 0
            client = OpenAIClient(settings)
            agent = CapacityAgent(
                client, max_rounds=settings.max_rounds, secrets=(settings.api_key,)
            )
            question = args.question
        if question is not None:
            turn = agent.ask(question)
            print(
                json.dumps(asdict(turn), ensure_ascii=False, indent=2, allow_nan=False)
                if args.json
                else format_turn(turn)
            )
            return 1 if turn.status in {"error", "limited"} else 0
        print(
            "Capacity Agent / 容量规划 Agent\nEnter a question. / 输入问题。\n/help  /reset  /baseline on|off  /exit"
        )
        while True:
            try:
                question = input("You / 用户: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye. / 已退出。")
                return 0
            if not question:
                continue
            if question.lower() in {"/exit", "exit", "quit", "退出"}:
                return 0
            if question == "/reset":
                agent.reset()
                print("Conversation cleared. / 会话已清空。")
                continue
            if question in {"/baseline on", "/baseline off"}:
                agent.baseline_enabled = question.endswith(" on")
                print(
                    "Baseline defaults enabled. / 已允许基准默认值。"
                    if agent.baseline_enabled
                    else "Baseline defaults disabled. / 已禁用基准默认值。"
                )
                continue
            if question == "/help":
                print(
                    "Ask for capacity, scenario comparison or PUE sensitivity.\n可询问容量、场景比较或 PUE 敏感性。\n/reset clears conversation; /baseline on permits documented defaults; /exit quits.\n/reset 清空会话；/baseline on 允许文档默认值；/exit 退出。"
                )
                continue
            print("Working... / 正在计算与组织回答…")
            try:
                turn = agent.ask(question)
            except KeyboardInterrupt:
                agent.reset()
                print(
                    "Request cancelled; conversation cleared. / 已取消请求并清空会话。"
                )
                continue
            print(
                json.dumps(asdict(turn), ensure_ascii=False, indent=2, allow_nan=False)
                if args.json
                else format_turn(turn)
            )
    except ImportError:
        print(
            "Install requirements-agent-lock.txt first. / 请先安装 requirements-agent-lock.txt。",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print("\nCancelled. / 已取消。")
        return 130
    except Exception:  # noqa: BLE001 -- CLI boundary must not reveal credentials.
        # Never dump remote exception bodies or credentials into the terminal.
        print(
            "Agent could not complete the request. Check local configuration and dependencies. / Agent 未能完成请求，请检查本地配置与依赖。",
            file=sys.stderr,
        )
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
