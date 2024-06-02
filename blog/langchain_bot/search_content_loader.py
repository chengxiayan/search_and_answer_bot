import concurrent
import os
import time
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Iterator

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

import utils
from constants import GOOGLE_API_KEY, GOOGLE_CSE_ID

logger = utils.get_logger(__name__)


class SearchContentLoader(BaseLoader):
    """Load HTML pages using `WebBaseLoader` and parse them with `BeautifulSoup'."""
    LOAD_URL_TIMEOUT = 10

    # threadpool
    threadpool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def __init__(
            self,
            query_key_words: str = "",
            num_results: int = 7
    ) -> None:
        self.query_key_words = query_key_words
        self.num_results = num_results

    def lazy_load(self) -> Iterator[Document]:
        start_ms = time.time()
        try:
            r = self.fetch_search_result()
            return r[:self.num_results] if r is not None else []
        except Exception as e:
            logger.exception("lazy_load.load web data failed.")
            return []
        finally:
            logger.info("lazy_load.load all data in %f seconds", time.time() - start_ms)

    @staticmethod
    def extract_content(search_result_obj):
        link = search_result_obj['link']
        if link:
            start_time_ms = time.time()
            success_flag = True
            try:
                # If you are within the Great Firewall, you can set up a proxy.
                web_base_loader = WebBaseLoader(link, verify_ssl=True, continue_on_failure=True,
                                                requests_per_second=10,
                                                proxies=dict(
                        http = 'http://127.0.0.1:7890',
                        https = 'http://127.0.0.1:7890',
                    )
                                                )
                web_base_loader.requests_kwargs = {'verify': False, 'timeout': SearchContentLoader.LOAD_URL_TIMEOUT}
                web_base_loader.session.get_adapter("https://").max_retries = 1
                data = web_base_loader.load()
                return data
            except Exception as e:
                logger.exception("error while loading url:%s",link)
                success_flag = False
                return None
            finally:
                logger.info("load url success=%s,time elapsed=%f,the url is:%s", success_flag, time.time() - start_time_ms, link)
        else:
            return None

    @staticmethod
    def filter_docs(docs: list):
        return [doc[0] for doc in docs if doc and doc[0] and doc[0].metadata.get('title') and  doc[0].metadata.get('title')!= 'Error']

    def fetch_search_result(self):

        search_engine = GoogleSearchAPIWrapper(google_api_key=GOOGLE_API_KEY, google_cse_id=GOOGLE_CSE_ID)
        # 因为后面还需要过滤一些网址，或者一些网址拿不到结果，这里会增大一点
        search_engine_result = search_engine.results(query=self.query_key_words, num_results=(self.num_results + 3))
        if search_engine_result is None or search_engine_result[0].get(
                'Result') == 'No good Google Search Result was found':
            logger.warning("fetch_search_result:No Google Search Result was found")

        try:
            futures = {SearchContentLoader.threadpool_executor.submit(SearchContentLoader.extract_content, result) for result in search_engine_result}
            done_futures = wait(futures, timeout=SearchContentLoader.LOAD_URL_TIMEOUT)
            done_results = [f.result() for f in done_futures[0]]
            return SearchContentLoader.filter_docs(done_results)
        except Exception as e:
            logger.exception("fetch_search_result.thread wait failed.")
            raise Exception("No Google Search Result was found")