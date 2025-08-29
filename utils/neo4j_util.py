import os
from string import Template
from typing import List

from langchain_community.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from langchain_core.prompts import SystemMessagePromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI, OpenAI

from utils.config import config


def test_neo4j_data(doc):
    nodes = ['公司', '人物', '地点', '时间', '组织机构']
    system_template = config.get('graph_prompt')
    template = Template(system_template)
    humn_str = f"你是一个知识图谱工程专家，请帮我提取出上下文中的文本中的 {','.join(nodes)} 等实体和关系以及适当的描述信息"
    humn = HumanMessagePromptTemplate.from_template(humn_str)
    datas = []
    # for doc in doc_list:
    sysprompt = template.safe_substitute(entity_types=','.join(nodes),
                                         input_text=doc)
    system_message_prompt = SystemMessagePromptTemplate.from_template(sysprompt)
    prompt = ChatPromptTemplate.from_messages([system_message_prompt, humn])

    llm = ChatOpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
               base_url="https://api.deepseek.com/v1",
               model="deepseek-chat")


    graph = LLMGraphTransformer(llm=llm, prompt=prompt, allowed_nodes=nodes, node_properties=True)
    document = Document(page_content=doc)
    res_data: List[GraphDocument] = graph.convert_to_graph_documents([document])
    ## 导入图库
    data = res_data[0]
    data_str = data.json()
    # retriever.new_nebula_graph_add(graph_space_name, [data_str])
    datas.append(data_str)
    print(data_str)




if __name__ == '__main__':
    str ="""
        DeepSeek，全称杭州深度求索人工智能基础技术研究有限公司 [40]。DeepSeek是一家创新型科技公司 [3]，成立于2023年7月17日 [40]，使用数据蒸馏技术 [41]，得到更为精炼、有用的数据 [41]。由知名私募巨头幻方量化孕育而生 [3]，专注于开发先进的大语言模型（LLM）和相关技术 [40]。注册地址 [6]：浙江省杭州市拱墅区环城北路169号汇金国际大厦西1幢1201室 [6]。法定代表人为裴湉 [6]，经营范围包括技术服务、技术开发、软件开发等 [6]。
        2024年1月5日至6月，相继发布DeepSeek LLM、DeepSeek-Coder、DeepSeekMath、DeepSeek-VL、DeepSeek-V2、DeepSeek-Coder-V2模型。 [9]2024年9月5日，更新API支持文档，宣布合并DeepSeek Coder V2和DeepSeek V2 Chat，推出DeepSeek V2.5 [7]。12月13日，发布DeepSeek-VL2 [9]。12月26日，正式上线DeepSeek-V3首个版本并同步开源 [1-2]。2025年1月31日，英伟达宣布DeepSeek-R1模型登陆NVIDIANIM。同一时段内，亚马逊和微软也接入DeepSeek-R1模型。 [49]2月5日，DeepSeek-R1、V3、Coder等系列模型，已陆续上线国家超算互联网平台。 [65]2月6日消息，澳大利亚政府以所谓“担心安全风险”为由，已禁止在所有政府设备中使用DeepSeek。 [68]2月8日，DeepSeek正式登陆苏州，并在苏州市公共算力服务平台上完成部署上线，为用户提供开箱即用的软硬件一体服务。 [82]截至2月9日，DeepSeek App的累计下载量已超1.1亿次，周活跃用户规模最高近9700万。 [154]2月20日消息，已有超200家企业宣布接入DeepSeek。 [147]2月26日，DeepSeek宣布开源DeepGEMM。 [176]
        发展历程
        早期发展
        DeepSeek成立于2023年7月17日，由知名量化资管巨头幻方量化创立。 [4]DeepSeek是一家创新型科技公司，长久以来专注于开发先进的大语言模型（LLM）和相关技术，作为大厂外唯一一家储备万张A100芯片的公司，幻方量化为DeepSeek的技术研发提供了强大的硬件支持。 [3]
        2023年8月2日，注册资本变更为1000万元，章程备案，投资人变更为宁波程恩企业管理咨询合伙企业（有限合伙），市场主体类型变更为其他有限责任公司。 [6]
        2024年5月7日，DeepSeek发布了MoE架构的DeepSeek V2。两天后，第一财经技术中心就对DeepSeek发布的技术报告和模型进行了深度分析与研究。经过严谨的评估，团队认为DeepSeek V2在架构设计、性能表现等方面与财经垂类大模型的需求高度契合，于是果断决定将基座模型迁移至DeepSeek V2，并迅速启动了以DeepSeek V2为主力基座模型的财经垂类大模型的训练与应用研发工作。 [53]
        2024年9月5日，DeepSeek官方更新API支持文档，宣布合并DeepSeek Coder V2和DeepSeek V2 Chat两个模型，升级推出全新的DeepSeek V2.5新模型。官方表示为向前兼容，API用户通过deepseek-coder或deepseek-chat均可以访问新的模型。 [7]
        2024年12月，DeepSeek开源大模型DeepSeek-V2的关键开发者之一罗福莉将加入小米，或供职于小米AI实验室，领导小米大模型团队。 [5]同月，一份关于DeepSeek发布历程、优化方向的专家会议纪要文件在业内流传。对此，DeepSeek 回应称，公司未授权任何人员参与券商投资者交流会，所谓“DeepSeek专家”非公司人员，所交流信息不实。DeepSeek表示，公司内部制定有严格的规章制度，明令禁止员工接受外部访谈、参与投资者交流等市场上各类面向投资者的机构信息交流会。相关事项均以公开披露信息为准。 [8]
        模型爆火
        2025年1月下旬，DeepSeek的R1模型发布后的一周内，DeepSeek刷屏美国各大主流媒体和社交网站。其中一部分原因为，TMT Breakout在与网友的讨论中，隐隐将英伟达周五下跌的原因指向DeepSeek的爆火。即R1的成功可能削弱了市场对英伟达AI芯片需求的预期，导致交易员做空英伟达股票，进而引发股价下跌。 [12]1月22日，美国媒体Business Insider报道称，DeepSeek-R1模型秉承开放精神，完全开源，为美国AI玩家带来了麻烦。开源的先进AI可能挑战那些试图通过出售技术赚取巨额利润的公司。 [15]
        2025年1月26日，有网友反应，DeepSeek崩了，提示服务器繁忙。新浪科技询问DeepSeek今天下午是否有闪崩时，DeepSeek回应称：1月26日下午DeepSeek确实出现了局部服务波动，但问题在数分钟内得到解决。此次事件可能与新模型发布后的访问量激增有关，而官方状态页未将其标记为事故。 [14]
        2025年1月27日，来自国产大模型公司“深度求索”的DeepSeek应用登顶苹果美国地区应用商店免费APP下载排行榜，在美区下载榜上超越了ChatGPT。同日，苹果中国区应用商店免费榜显示，DeepSeek成为中国区第一 [17]。
        2025年1月27日，DeepSeek服务状态页面显示，DeepSeek网页/API不可用，目前正在调查该问题。 [16]对于DeepSeek网页/API不可用的原因，DeepSeek回应称，可能和服务维护、请求限制等因素有关。 [18]1月27日晚，DeepSeek服务再次“宕机”，DeepSeek服务状态页面显示，DeepSeek网页不可用，公司正在调查这一问题。 [21]1月27日，DeepSeek服务状态页面显示，20点55分，DeepSeek对话服务已恢复，账号服务仍存在问题，用户或无法登录及注册。21点05分，DeepSeek更新称，将继续监测故障。 [22]
        当地时间2025年1月27日，纳斯达克股指出现3%下跌，原因是中国人工智能公司DeepSeek模型引发美国投资者关注。央视记者在纳斯达克交易所现场对纳斯达克副主席麦柯奕进行了采访。麦柯奕表示，他认为，DeepSeek将是人工智能领域革命的重要组成部分。 [25]
        当地时间2025年1月27日晚，美国总统特朗普在佛罗里达州迈阿密发表讲话时，对中国人工智能初创公司DeepSeek搅动纳斯达克一事表示，DeepSeek的出现“给美国相关产业敲响了警钟”，美国“需要集中精力赢得竞争”。特朗普同时表示，他认为，DeepSeek的模型高效且经济，其出现是一种积极的发展。 [26]1月27日，英国《金融时报》发表评论文章说，中国初创企业深度求索（DeepSeek）最近在人工智能领域获得重大突破，其发布的开源模型DeepSeek-R1对全球用户产生极大吸引力，有利于推动人工智能技术的开发和应用。 [27]1月27日，中国深度求索（DeepSeek）公司发布的最新开源模型引起热议。美国媒体报道称，这是人工智能领域的一场“地震”，“从华盛顿到华尔街再到硅谷都感受到了震动”。美国经济学家布莱恩·雅各布森表示，这可能会改变人工智能的叙事，“我们确实需要担心这一趋势可能带来的影响。”布莱恩·雅各布森同时表示，这说明美国对华出口芯片限制显然没有那么有效，或许能看到美国政府的一些政策发生变化，从关税、禁运和限制方面转向更多地补贴和激励美国国内技术的发展。 [30]
        受到攻击
        2025年1月27日晚至1月28日凌晨 [139]，DeepSeek于服务状态页面先是公告称：“近期DeepSeek线上服务受到大规模恶意攻击，为持续提供服务，暂时限制了+86手机号以外的注册方式，已注册用户可以正常登录” [23]，后通过官方服务状态又发布声明，将“暂时限制了+86手机号以外的注册方式”的措辞改为“注册可能繁忙，请稍等重试” [139]。
        2025年1月28日凌晨，DeepSeek在GitHub平台发布了Janus-Pro多模态大模型，进军文生图领域。 [24]
        当地时间2025年1月28日，据央视新闻报道，美国新任白宫新闻秘书卡罗琳·莱维特（KarolineLeavitt）进行了她的首次简报会，其中提及了中国人工智能初创公司深度求索（DeepSeek）。关于DeepSeek，莱维特表示，特朗普认为该公司发布的人工智能模型是对美国人工智能行业的一个警钟。她同时称，白宫正在努力“确保美国人工智能的主导地位”，特朗普此前签署行政命令撤销了对人工智能行业的一些繁琐监管。 [32]
        2025年1月28日，深度求索（DeepSeek）官网显示，其线上服务受到大规模恶意攻击，谭主向奇安信安全专家咨询并独家了解到，DeepSeek这次受到的网络攻击，IP地址都在美国。 [33]同日，美国多名官员回应DeepSeek对美国的影响，表示DeepSeek是“偷窃”，正对其影响开展国家安全调查。 [34]
        2025年1月28日，意大利数据保护机构表示，正在向中国人工智能 (AI) 模型DeepSeek寻求有关其使用个人数据的解释。 意大利监管机构Garante表示，希望了解收集了哪些个人数据、从哪些来源收集、用于什么目的、基于什么法律依据，以及是否存储在中国。Garante在一份声明中表示，DeepSeek及其附属公司有20天的时间答复，这是针对这家中国初创公司的首批监管举措之一。在美国，白宫新闻秘书表示官员们正在调查该应用程序对国家安全的影响。 [35]
        2025年1月29日，360集团创始人周鸿祎表示，如果DeepSeek有需要，360愿意提供网络安全方面的全力支持。中国红客联盟发布公告，DeepSeek遭受攻击关乎整个国家的网络安全以及技术创新环境。 [46]
    """

    test_neo4j_data(str)

