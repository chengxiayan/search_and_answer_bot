# google搜索引擎id
GOOGLE_CSE_ID = ""
#google API key
GOOGLE_API_KEY = ""
#OpenAI key
OPENAI_API_KEY = ""
#OpenAI url
OPENAI_BASE_URL = "https://gtapi.xiaoerchaoren.com:8932/v1"
#langchain API key
LANGSMITH_API_KEY = ""
#langsmith url
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
#moonshot
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
MOONSHOT_API_KEY = ""

# 用户对话prompt模板
PEDIA_PROMPT_USER = """
在收到用户查询（query）后，对该查询给简洁、准确、客观的答复，并且以维基百科的语气进行撰写。不要提供与查询无关的信息，也不要重复。
你将获得一组与从网络检索到的查询相关的上下文，每段上下文都以“[x]”的序号开头，上下文的内容为yaml格式，其中“x”是该段上下文的索引，它是一个数字，例如1,2,3,4。
请基于上下文的内容总结产生回答内容，在总结内容中，可以给每个句子末尾加上引用信息（如果适用），表示这段内容来源于哪一段上下文，引用的格式为"[i]"，其中i需要替换为具体的数字，即其引用的上下文的段落序号，示例：“科学是人类进步的阶梯[1]”;
如果一个句子来自多段上下文，请列出所有适用的引文，例如“科技是第一生产力[1][3]”。
## 限制
1. 回复必须以用户喜欢的语言编写,如果用户未指定任何首选语言，请使用用户在查询中使用的相同语言。
2. 不要盲目地逐字重复这些上下文。将其用作推理过程的证据来源。*您必须写下自己的答案。不要仅仅提供引文。 * 如果给定的上下文没有提供足够的信息，请说“信息缺失”，然后说出相关主题。
3. 你的回复应长于 128 个单词且少于 1024 个单词。
-----
这是用户查询（query）：
{query}
-----
这是检索到检索到的查询相关的上下文（context）：
{context}
"""