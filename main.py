import config
from src import CrawlerProcess


if __name__ == "__main__":
    p = CrawlerProcess(file_name=config.INPUT_FILE)
    p.run()
