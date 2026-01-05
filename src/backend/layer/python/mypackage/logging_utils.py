import logging

def get_logger(name: str = __name__) -> logging.Logger:

    # ロガー自体は何度呼んでも同じものを返す
    logger = logging.getLogger(name)

    # すでにハンドラがあれば、addHandlerしない（ログ出力の重複防止）
    if not logger.handlers:
        # フォーマッターをハンドラーに紐づけ、ロガーに紐づける
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return logger

# テスト用コード
if __name__ == "__main__":
    logger = get_logger()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")   