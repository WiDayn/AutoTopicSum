import string
import jieba
from sentence_transformers import SentenceTransformer, util


class TextMatcher:
    def __init__(self):
        # 加载多语言预训练模型（支持中英混杂文本）
        # 模型说明：https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # 通用停用词（中英文通用虚词/无意义词）
        self.stopwords = {
            # 中文停用词
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也',
            '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '但', '而',
            # 英文停用词
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'of', 'for',
            'with', 'as', 'by', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }

    def _preprocess_mixed_text(self, text):
        """
        处理中英文混杂文本的预处理
        步骤：去标点 → 中文分词 → 过滤停用词 → 保留英文原词（按空格拆分）
        """
        if not text.strip():
            return ""

        # 1. 去除标点符号（保留字母、数字、中文）
        # 构建允许保留的字符集：中文、英文、数字、空格
        allowed_chars = set(
            string.ascii_letters + string.digits + ' ' + ''.join([chr(c) for c in range(0x4e00, 0x9fff + 1)]))
        text_clean = ''.join([c for c in text if c in allowed_chars])

        # 2. 中文分词（英文按空格拆分，不额外处理）
        # 使用jieba分词，同时保留英文单词（通过cut_all=False确保精度）
        tokens = jieba.cut(text_clean, cut_all=False)

        # 3. 过滤停用词和空字符
        filtered_tokens = []
        for token in tokens:
            token = token.strip()
            if token and token.lower() not in self.stopwords:  # 忽略大小写判断停用词
                filtered_tokens.append(token)

        # 4. 用空格拼接 tokens（模型输入需字符串格式）
        return ' '.join(filtered_tokens)

    def calculate_similarity(self, event_text, news_titles):
        """
        计算事件文本与新闻标题的相似度（支持中英文混杂）
        :param event_text: 用户输入的事件（可混杂中英文）
        :param news_titles: 新闻标题列表（可混杂中英文）
        :return: 相似度列表（0~1，值越高关联度越强）
        """
        # 1. 预处理所有文本（事件+标题）
        processed_event = self._preprocess_mixed_text(event_text)
        processed_titles = [self._preprocess_mixed_text(title) for title in news_titles]

        # 2. 处理空文本（避免模型编码报错）
        processed_event = processed_event if processed_event else "空文本"
        processed_titles = [title if title else "空文本" for title in processed_titles]

        # 3. 用多语言模型将文本转为语义向量
        event_embedding = self.model.encode(processed_event, convert_to_tensor=True)
        title_embeddings = self.model.encode(processed_titles, convert_to_tensor=True)

        # 4. 计算余弦相似度（语义层面的匹配，而非字面匹配）
        similarities = util.cos_sim(event_embedding, title_embeddings).flatten().tolist()

        return similarities