from datetime import datetime
from pathlib import Path

from app.paths import tokens_log_for_folder


def calculate_usage_cost(model_prices: dict, model_name: str, usage_metadata) -> float:
    in_tokens = usage_metadata.prompt_token_count
    out_tokens = usage_metadata.candidates_token_count
    prices = model_prices.get(model_name, (0.0, 0.0))
    return (in_tokens / 1_000_000 * prices[0]) + (out_tokens / 1_000_000 * prices[1])


def append_usage_log(folder: str, model_prices: dict, model_name: str, usage_metadata) -> None:
    log_path = tokens_log_for_folder(folder)
    cost = calculate_usage_cost(model_prices, model_name, usage_metadata)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = (
        f"{now};{model_name};{usage_metadata.prompt_token_count};"
        f"{usage_metadata.candidates_token_count};{cost:.6f}\n"
    )

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(log_line)


def read_usage_log(folder: str) -> tuple[list[tuple[str, str, str, str, str]], float]:
    log_path = Path(tokens_log_for_folder(folder))
    row_data = []
    total_cost = 0.0

    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split(";")
            if len(parts) == 5:
                row_data.append(tuple(parts))
                total_cost += float(parts[4])

    return row_data, total_cost
