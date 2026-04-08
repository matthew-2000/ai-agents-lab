"""Tool definitions for 01 - Tool-Using Assistant."""

from __future__ import annotations

import ast
import json
import re
import ssl
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from config import DATA_DIR


@dataclass(frozen=True)
class ToolDefinition:
    """Defines one callable tool exposed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]

    def to_response_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def load_json_file(path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_weather_snapshots() -> list[dict[str, Any]]:
    return load_json_file(DATA_DIR / "weather_snapshots.json")


def load_knowledge_base() -> list[dict[str, Any]]:
    return load_json_file(DATA_DIR / "knowledge_base.json")


def load_prompt_examples() -> list[dict[str, Any]]:
    return load_json_file(DATA_DIR / "prompt_examples.json")


def load_prompt_example_map() -> dict[str, dict[str, Any]]:
    examples = load_prompt_examples()
    return {example["id"]: example for example in examples}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def format_number(value: float | int) -> float | int:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return round(value, 8) if isinstance(value, float) else value


def safe_calculate(expression: str) -> dict[str, Any]:
    if len(expression) > 120:
        raise ValueError("Expression is too long for the demo calculator.")

    tree = ast.parse(expression, mode="eval")

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = eval_node(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)

            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                if abs(right) > 10 or abs(left) > 1_000_000:
                    raise ValueError("Exponentiation request is outside safe demo limits.")
                return left**right

        raise ValueError("Unsupported calculator expression.")

    result = eval_node(tree)
    return {
        "expression": expression,
        "result": format_number(result),
    }


def http_get_json(base_url: str, params: dict[str, Any], timeout_seconds: int = 10) -> dict[str, Any]:
    query_string = urlencode(params)
    request_url = f"{base_url}?{query_string}"
    ssl_context = ssl.create_default_context()

    try:
        import certifi
    except ImportError:
        certifi = None

    if certifi is not None:
        ssl_context = ssl.create_default_context(cafile=certifi.where())

    with urlopen(request_url, timeout=timeout_seconds, context=ssl_context) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def build_calculator_tool() -> ToolDefinition:
    def handler(expression: str) -> dict[str, Any]:
        return {
            "status": "ok",
            "tool": "calculator",
            **safe_calculate(expression),
        }

    return ToolDefinition(
        name="calculator",
        description="Evaluate a basic arithmetic expression exactly.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression such as 17 * 24 or (5 + 3) / 2.",
                }
            },
            "required": ["expression"],
        },
        handler=handler,
    )


def format_live_location(result: dict[str, Any]) -> str:
    parts = [result.get("name"), result.get("admin1"), result.get("country")]
    return ", ".join(part for part in parts if part)


def fallback_weather_lookup(
    location: str,
    weather_snapshots: list[dict[str, Any]],
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    alias_map: dict[str, dict[str, Any]] = {}
    for snapshot in weather_snapshots:
        for alias in snapshot["aliases"]:
            alias_map[normalize_text(alias)] = snapshot

    normalized = normalize_text(location)
    selected = alias_map.get(normalized)

    if selected is None:
        for alias, snapshot in alias_map.items():
            if alias in normalized or normalized in alias:
                selected = snapshot
                break

    if selected is None:
        result = {
            "status": "not_found",
            "tool": "get_weather",
            "requested_location": location,
            "available_locations": sorted(
                {snapshot["location"] for snapshot in weather_snapshots}
            ),
            "note": "Live weather lookup failed and no local fallback matched the requested location.",
        }
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        return result

    result = {
        "status": "ok",
        "tool": "get_weather",
        "source": "mock_fallback",
        "location": selected["location"],
        "date": selected["date"],
        "condition": selected["condition"],
        "temperature_c": selected["temperature_c"],
        "feels_like_c": selected["feels_like_c"],
        "humidity_pct": selected["humidity_pct"],
        "wind_kph": selected["wind_kph"],
        "note": "Open-Meteo was unavailable, so this answer uses mocked local fallback weather data.",
    }
    if fallback_reason:
        result["fallback_reason"] = fallback_reason
    return result


def live_weather_lookup(location: str) -> dict[str, Any]:
    geocoding_data = http_get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )

    results = geocoding_data.get("results") or []
    if not results:
        raise ValueError(f"Open-Meteo could not find a location matching '{location}'.")

    best_match = results[0]
    forecast_data = http_get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": best_match["latitude"],
            "longitude": best_match["longitude"],
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "timezone": "auto",
            "forecast_days": 1,
        },
    )

    current = forecast_data.get("current")
    if not current:
        raise ValueError("Open-Meteo returned no current weather block.")

    weather_code = current.get("weather_code")
    condition = WEATHER_CODE_MAP.get(weather_code, f"Weather code {weather_code}")
    return {
        "status": "ok",
        "tool": "get_weather",
        "source": "open_meteo",
        "location": format_live_location(best_match),
        "date": current.get("time"),
        "condition": condition,
        "temperature_c": current.get("temperature_2m"),
        "feels_like_c": current.get("apparent_temperature"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "wind_kph": current.get("wind_speed_10m"),
        "timezone": forecast_data.get("timezone"),
        "note": "Weather data comes from the live Open-Meteo API.",
    }


def build_weather_tool(
    weather_snapshots: list[dict[str, Any]],
    enable_live_weather: bool,
) -> ToolDefinition:
    def handler(location: str) -> dict[str, Any]:
        if not enable_live_weather:
            return fallback_weather_lookup(location, weather_snapshots)

        try:
            return live_weather_lookup(location)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return fallback_weather_lookup(
                location,
                weather_snapshots,
                fallback_reason=str(exc),
            )

    return ToolDefinition(
        name="get_weather",
        description="Look up current weather, using the live Open-Meteo API with a local fallback.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or city and country, such as Rome or New York.",
                }
            },
            "required": ["location"],
        },
        handler=handler,
    )


def build_knowledge_base_tool(knowledge_base: list[dict[str, Any]]) -> ToolDefinition:
    def handler(query: str) -> dict[str, Any]:
        query_tokens = tokenize(query)
        scored_entries: list[tuple[int, dict[str, Any]]] = []

        for entry in knowledge_base:
            keywords = set(entry.get("keywords", []))
            score = len(query_tokens & keywords)
            if score:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: (-item[0], item[1]["title"].lower()))

        matches = [
            {
                "title": entry["title"],
                "content": entry["content"],
                "score": score,
            }
            for score, entry in scored_entries[:3]
        ]

        status = "ok" if matches else "not_found"
        return {
            "status": status,
            "tool": "search_knowledge_base",
            "query": query,
            "matches": matches,
            "note": "This tool searches only the local demo knowledge base bundled with the project.",
        }

    return ToolDefinition(
        name="search_knowledge_base",
        description="Search a small local knowledge base for demo facts and project context.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in the local knowledge base.",
                }
            },
            "required": ["query"],
        },
        handler=handler,
    )


def build_tools(enable_live_weather: bool = True) -> list[ToolDefinition]:
    weather_snapshots = load_weather_snapshots()
    knowledge_base = load_knowledge_base()
    return [
        build_calculator_tool(),
        build_weather_tool(
            weather_snapshots=weather_snapshots,
            enable_live_weather=enable_live_weather,
        ),
        build_knowledge_base_tool(knowledge_base),
    ]
