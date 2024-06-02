import logging

from langchain_openai import ChatOpenAI

import constants


def get_logger(name,log_level=logging.INFO):
    """构造日志logger"""
    # Create a logger
    logger = logging.getLogger(name)
    # Create a handler
    handler = logging.StreamHandler()
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set the formatter for the handler
    handler.setFormatter(formatter)
    # Add the handler to the logger
    logger.addHandler(handler)
    # Set the log level
    logger.setLevel(log_level)
    return logger


def get_llm(model: str = 'chatgpt'):
    """获取模型"""
    if model == 'chatgpt':
        return ChatOpenAI(model_name="gpt-4-turbo", base_url=constants.OPENAI_BASE_URL, api_key=constants.OPENAI_API_KEY)
    elif model == 'moonshot':
        return ChatOpenAI(model_name="moonshot-v1-128k", base_url=constants.MOONSHOT_BASE_URL,api_key=constants.MOONSHOT_API_KEY)
    else:
        raise "model not supported,model="+model