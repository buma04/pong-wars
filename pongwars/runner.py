from __future__ import annotations

import argparse
from pathlib import Path

from pongwars.config import load_config
from pongwars.game import PongWarsGame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="game_config.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    game = PongWarsGame(config)
    game.run()
