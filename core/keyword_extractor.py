import spacy
from spacy.language import Language
from typing import List, Dict, Optional, Set


class KeywordExtractor:
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        初始化实体提取器

        :param model_name: spaCy预训练模型名称，默认为英文小型模型
                          中文可使用"zh_core_web_sm"，其他语言参考spaCy官方模型列表
        """
        try:
            # 加载spaCy模型
            self.nlp: Language = spacy.load(model_name)
            self.model_name = model_name
            print(f"成功加载模型: {model_name}")
        except OSError:
            raise ValueError(
                f"模型 {model_name} 未安装，请先执行命令安装:\n"
                f"python -m spacy download {model_name}"
            )

        # 初始化实体去重集合
        self.seen_entities: Set[str] = set()

    def text_cleaner(self, text: str) -> str:
        """
        文本预处理：清除多余空格和特殊字符

        :param text: 原始文本
        :return: 清洗后的文本
        """
        if not text or not isinstance(text, str):
            return ""

        # 去除多余空格
        cleaned = " ".join(text.strip().split())
        return cleaned

    def input_text_entities_extractor(
            self,
            text: str,
            filter_types: Optional[List[str]] = None,
            deduplicate: bool = True
    ) -> List[Dict[str, str]]:
        """
        从文本中提取实体

        :param text: 待处理文本
        :param filter_types: 实体类型过滤列表，如["PERSON", "ORG"]，为None则返回所有类型
        :param deduplicate: 是否去除重复实体
        :return: 实体列表，每个实体包含"text"(实体文本)和"type"(实体类型)
        """
        # 文本预处理
        cleaned_text = self.text_cleaner(text)
        if not cleaned_text:
            return []

        # 使用spaCy处理文本
        doc = self.nlp(cleaned_text)

        entities: List[Dict[str, str]] = []

        for ent in doc.ents:
            # 实体文本和类型
            entity_text = ent.text.strip()
            entity_type = ent.label_

            # 过滤指定类型的实体
            if filter_types and entity_type not in filter_types:
                continue

            # 去重处理
            if deduplicate:
                if entity_text in self.seen_entities:
                    continue
                self.seen_entities.add(entity_text)

            entities.append({
                "text": entity_text,
                "type": entity_type
            })

        return entities

    def clear_seen_entities(self) -> None:
        """清空已见实体集合，用于处理新的文本批次"""
        self.seen_entities.clear()

    def get_supported_entity_types(self) -> List[str]:
        """获取当前模型支持的实体类型列表"""
        return list(self.nlp.pipe_labels["ner"])


# 示例用法
if __name__ == "__main__":
    # 初始化提取器（英文）
    extractor = KeywordExtractor(model_name="en_core_web_sm")

    # 打印支持的实体类型
    print("支持的实体类型:", extractor.get_supported_entity_types())

    # 待处理文本
    text = """
    Apple is planning to open a new store in Paris next month. 
    CEO Tim Cook announced the news during an interview with CNN.
    """

    # 提取所有实体
    all_entities = extractor.input_text_entities_extractor(text=text)
    print("\n所有实体:")
    for ent in all_entities:
        print(f"{ent['text']} ({ent['type']})")

    # 提取指定类型实体（仅人物和组织）
    extractor.clear_seen_entities()  # 清空之前的去重记录
    filtered_entities = extractor.input_text_entities_extractor(
        text=text,
        filter_types=["PERSON", "ORG"]
    )
    print("\n过滤后的实体:")
    for ent in filtered_entities:
        print(f"{ent['text']} ({ent['type']})")
