from game.core import Game


def main() -> None:
    try:
        game = Game()
        game.run()
    except Exception as exc:
        print("游戏运行出错:", exc)


if __name__ == "__main__":
    main()
