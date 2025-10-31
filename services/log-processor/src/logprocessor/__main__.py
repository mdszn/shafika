from .logprocessor import LogProcessor


def main() -> None:
  print("Starting log processor...")
  processor = LogProcessor(queue_name="logs", max_workers=10000)
  processor.run()


if __name__ == "__main__":
  main()

