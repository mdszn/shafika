from .processor import BlockProcessor


def main() -> None:
  print("Starting block processor worker")
  processor = BlockProcessor()
  processor.run()


if __name__ == "__main__":
  main()

