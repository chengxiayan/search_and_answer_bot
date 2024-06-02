import os
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableParallel
from langsmith import Client

import utils
from constants import LANGSMITH_API_KEY, PEDIA_PROMPT_USER
from search_content_loader import SearchContentLoader

logger = utils.get_logger(__name__)
client = Client(api_key = LANGSMITH_API_KEY)


def clean_source_text(text):
    if text is None:
        return None
    cleaned_text = text.strip()
    cleaned_text = re.sub(r'(\n){4,}', '\n\n\n', cleaned_text)
    cleaned_text = re.sub(r'\n\n', ' ', cleaned_text)
    cleaned_text = re.sub(r' {3,}', '  ', cleaned_text)
    cleaned_text = cleaned_text.replace('\t', '')
    cleaned_text = re.sub(r'\n+(\s*\n)*', '\n', cleaned_text)
    cleaned_text = re.sub(r'\[\d+\]','',cleaned_text)
    if len(cleaned_text)>4096:
        cleaned_text = cleaned_text[:4096]
    return cleaned_text


def cons_content_and_reference(doc_list:list):
    logger.info("cons_content_and_reference.start to format doc_list,size=%d" ,len(doc_list))
    content_template = """[{i}]
        ```YAML
        Title : {title}
        Source: {source}
        Content: {content}
        Link: {link}
        ```"""
    reference_template = """[{i}][{title}]({link})"""
    content_str_list=[]
    referentce_str_list=[]
    i = 0
    context_length = 0
    for index,doc in enumerate(doc_list):
        content = clean_source_text(doc.page_content)
        url = doc.metadata['source']
        source = doc.metadata['source']
        title = doc.metadata['title']
        if url and content and source and title:
            i+=1
            content_str = content_template.format(i=i,title=title,source=source,content=content,link=url)
            if context_length+len(content_str)>100000:
                break
            content_str_list.append(content_str)
            referentce_str_list.append(reference_template.format(i=i,title=title,source=source,content=content,link=url))
            context_length+=len(content_str)

    return {"context":"\n\n".join(content_str_list),"reference":"\n".join(referentce_str_list)}


def fetch_data_by_search_engine(query:str):
    search_content_loader = SearchContentLoader(query,7)
    docs = search_content_loader.load()
    return cons_content_and_reference(docs)


def _extract_country_names_streaming(input_stream):
    """A function that operates on input streams."""
    reference = str()
    llm_content = str()
    last_length = 0
    for input in input_stream:
        # print(input, end="|", flush=True)
        if not isinstance(input, dict):
            continue

        if 'reference' in input:
            reference += input.get('reference')
        elif 'llm_content' in input:
            llm_content += input.get('llm_content')
        else:
            continue
        full_content = reference+"\n\n\n"+llm_content
        yield full_content[last_length:]
        last_length = len(full_content)


def cons_summarize_chain():
    llm = utils.get_llm(model='moonshot')
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
你是一个信息总结摘要大师，有能力去分析处理多个来源的信息，并找出其中的重点进行总结，对于有可能的谬误，你会综合所有内容去评估剔除。你的处理过程依赖的是逻辑思考，而不是直觉。此外，你也是一个专业作家，能够巧妙地连贯地组织您的思想和论点，确保你的文字引人入胜。
""",
            ),
            ("user", PEDIA_PROMPT_USER),
        ]
    )

    main_chain = ({'extra_content':lambda x:fetch_data_by_search_engine(x), 'query':RunnablePassthrough()}|
                  RunnablePassthrough.assign(context = RunnableLambda(lambda x:x.get('extra_content').get('context')),
                                             reference = RunnableLambda(lambda x:x.get('extra_content').get('reference')))).with_config(
        run_name="parse_content_reference",
    )
    # 这里其实就是要 main_chain 的执行结果可以输入给下游两个地方：
    # 1. content用于总结内容
    # 2. reference 用于构造引用信息
    # |prompt_template|llm)
    chain = (
            main_chain|
            RunnableParallel(llm_content=(prompt| llm| StrOutputParser()).with_config(run_name="llm_raw"),reference = RunnableLambda(lambda x:x.get('reference'))).with_config(
                run_name="llm_generate",
            )
            |
            _extract_country_names_streaming
    )
    return chain


def gen_ui(chain):
    import gradio as gr
    with gr.Blocks() as demo:
        chatbot = gr.Chatbot(height = 600)
        msg = gr.Textbox()
        clear = gr.Button("Clear")

        def user(user_message, history):
            return "", history + [[user_message, None]]

        def bot(history):
            history[-1][1] = ""
            for character in chain.stream({"input": history[-1][0]}):
                history[-1][1] += character
                yield history

        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        clear.click(lambda: None, None, chatbot, queue=False)

    demo.queue()
    demo.launch(share=True)


if __name__ == "__main__":

    os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    os.environ['LANGCHAIN_API_KEY'] = LANGSMITH_API_KEY
    # If you are within the Great Firewall, you can set up a proxy.
    os.environ['https_proxy'] = 'http://127.0.0.1:7890'
    os.environ['http_proxy'] = 'http://127.0.0.1:7890'

    summarize_chain = cons_summarize_chain()
    gen_ui(summarize_chain)
