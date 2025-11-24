"""分词服务模块"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class WordSegmentationService:
    """分词服务类"""
    
    def __init__(self):
        """初始化分词服务"""
        self._hanlp = None
        self._initialized = False
        logger.info("分词服务初始化中...")
    
    def _init_hanlp(self):
        """延迟初始化HanLP"""
        if self._initialized:
            return
        
        try:
            import hanlp
            # 优先加载支持 tok/fine + pos/pku + ner/pku 的多任务模型
            self._hanlp = hanlp.load(
                hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH
            )
            self._initialized = True
            logger.info("HanLP 多任务模型加载成功（支持 PKU 词性与 NER）")
        except Exception as e:
            logger.error(f"HanLP 多任务模型加载失败: {str(e)}")
            # 如果多任务模型不可用，回退到轻量级分词模型
            try:
                logger.info("尝试加载轻量级分词模型 (COARSE_ELECTRA_SMALL_ZH)...")
                self._hanlp = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
                self._initialized = True
                logger.info("HanLP 轻量级分词模型加载成功（仅提供分词能力）")
            except Exception as e2:
                logger.error(f"轻量级分词模型加载也失败: {str(e2)}")
                raise
    
    def segment(self, text: str) -> Dict[str, Any]:
        """
        对文本进行分词
        
        Args:
            text: 待分词的文本
            
        Returns:
            包含分词结果的字典
        """
        if not text or not text.strip():
            return {
                'success': False,
                'data': None,
                'message': '输入文本不能为空'
            }
        
        try:
            # 延迟初始化
            self._init_hanlp()
            
            if not self._hanlp:
                return {
                    'success': False,
                    'data': None,
                    'message': 'HanLP模型未初始化'
                }
            
            # 使用 PKU 标注体系
            try:
                result = self._hanlp(
                    text,
                    tasks=['tok/fine', 'pos/pku', 'ner/pku']
                )
                logger.debug(
                    "HanLP返回: type=%s keys=%s",
                    type(result),
                    list(result.keys()) if isinstance(result, dict) else 'N/A'
                )
                tokens = self._extract_list(result, ['tok/fine', 'tok', 'tok/coarse'])
                pos_tags = self._extract_list(result, ['pos/pku', 'pos', 'pos/ctb'])
                ner_entities = result.get('ner/pku', [])
                segments = []
                for idx, token in enumerate(tokens):
                    pos_tag = pos_tags[idx] if idx < len(pos_tags) else None
                    if pos_tag and isinstance(pos_tag, str):
                        pos_tag = pos_tag.strip()
                    pos_label = self._get_pos_label(pos_tag) if pos_tag else None
                    segments.append({
                        'word': token,
                        'pos': pos_tag,
                        'pos_label': pos_label,
                        'length': len(token)
                    })
                    logger.debug("词: %s, 词性: %s, 标签: %s", token, pos_tag, pos_label)
            except Exception as e:
                logger.warning(f"PKU 多任务调用失败，回退为仅分词模式: {str(e)}")
                tokens = self._ensure_list(self._hanlp(text))
                segments = [{
                    'word': token,
                    'pos': None,
                    'pos_label': None,
                    'length': len(token)
                } for token in tokens]
                ner_entities = []
            
            # 生成带词性的分词文本
            if segments and segments[0].get('pos'):
                segmented_text_with_pos = ' / '.join([
                    f"{seg['word']}({seg['pos']})" for seg in segments
                ])
            else:
                segmented_text_with_pos = ' / '.join([seg['word'] for seg in segments])
            
            return {
                'success': True,
                'data': {
                    'original_text': text,
                    'segments': segments,
                    'total_words': len(segments),
                    'segmented_text': ' / '.join([seg['word'] for seg in segments]),
                    'segmented_text_with_pos': segmented_text_with_pos,
                    'entities': self._format_entities(ner_entities)
                },
                'message': '分词成功'
            }
            
        except Exception as e:
            logger.error(f"分词失败: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': f'分词失败: {str(e)}'
            }
    
    def batch_segment(self, texts: List[str]) -> Dict[str, Any]:
        """
        批量分词
        
        Args:
            texts: 待分词的文本列表
            
        Returns:
            包含批量分词结果的字典
        """
        if not texts:
            return {
                'success': False,
                'data': None,
                'message': '输入文本列表不能为空'
            }
        
        try:
            # 延迟初始化
            self._init_hanlp()
            
            if not self._hanlp:
                return {
                    'success': False,
                    'data': None,
                    'message': 'HanLP模型未初始化'
                }
            
            results = []
            for text in texts:
                if not text or not text.strip():
                    continue
                
                result = self.segment(text)
                if result['success']:
                    results.append(result['data'])
            
            return {
                'success': True,
                'data': {
                    'results': results,
                    'total': len(results)
                },
                'message': '批量分词成功'
            }
            
        except Exception as e:
            logger.error(f"批量分词失败: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': f'批量分词失败: {str(e)}'
            }
    
    def _extract_list(self, result: Any, keys: List[str]) -> List[Any]:
        """按照候选键依次提取列表内容"""
        if not isinstance(result, dict):
            return []
        for key in keys:
            if key in result and result[key]:
                return self._ensure_list(result[key])
        return []
    
    def _ensure_list(self, value: Any) -> List[Any]:
        """确保返回列表形式"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]
    
    def _format_entities(self, entities: Any) -> List[Dict[str, Any]]:
        """将 HanLP 的 ner/pku 结果转换为统一结构"""
        formatted = []
        if not entities:
            return formatted
        for item in entities:
            text = None
            label = None
            start = None
            end = None
            if isinstance(item, dict):
                text = item.get('text') or item.get('word')
                label = item.get('label') or item.get('type')
                start = item.get('start')
                end = item.get('end')
            elif isinstance(item, (list, tuple)):
                if len(item) == 2:
                    text, label = item
                elif len(item) >= 3:
                    text = item[0]
                    start = item[1]
                    end = item[2]
                    label = item[3] if len(item) > 3 else item[-1]
            if text:
                formatted.append({
                    'text': text,
                    'label': label,
                    'start': start,
                    'end': end
                })
        return formatted
    
    def _get_pos_label(self, pos_tag: str) -> str:
        """
        获取词性标签的中文说明
        支持多种词性标注集：Penn Treebank、北大标注集等
        
        Args:
            pos_tag: 词性标签（如 'NN', 'NR', 'n', 'v' 等）
            
        Returns:
            词性标签的中文说明
        """
        # 处理空值或非字符串类型
        if not pos_tag:
            return '未知'
        
        # 转换为字符串并清理
        pos_tag = str(pos_tag).strip()
        if not pos_tag or pos_tag == 'UNKNOWN':
            return '未知'
        
        # 转换为小写以便统一处理
        pos_tag_lower = pos_tag.lower()
        pos_tag_upper = pos_tag.upper()
        
        # Penn Treebank 词性标注集（大写）
        ptb_labels = {
            # 名词类
            'NN': '名词', 'NNS': '名词复数', 'NNP': '专有名词单数', 'NNPS': '专有名词复数',
            'NR': '人名', 'NS': '地名', 'NT': '机构名', 'NZ': '其他专名',
            # 动词类
            'VB': '动词原形', 'VBD': '动词过去式', 'VBG': '动名词', 'VBN': '过去分词',
            'VBP': '动词现在式', 'VBZ': '动词第三人称单数',
            # 形容词类
            'JJ': '形容词', 'JJR': '形容词比较级', 'JJS': '形容词最高级',
            # 副词类
            'RB': '副词', 'RBR': '副词比较级', 'RBS': '副词最高级',
            # 数词类
            'CD': '数词',
            # 代词类
            'PRP': '人称代词', 'PRP$': '物主代词', 'WP': '疑问代词', 'WP$': '疑问物主代词',
            # 介词类
            'IN': '介词',
            # 连词类
            'CC': '并列连词',
            # 限定词
            'DT': '限定词',
            # 感叹词
            'UH': '感叹词',
            # 标点符号
            '.': '句号', ',': '逗号', ':': '冒号', ';': '分号', '?': '问号', '!': '叹号',
            # 其他
            'TO': 'to', 'MD': '情态动词', 'EX': '存在词', 'FW': '外来词',
            'LS': '列表标记', 'PDT': '前置限定词', 'POS': '所有格标记', 'RP': '小品词',
            'SYM': '符号', 'WDT': '疑问限定词', 'WRB': '疑问副词'
        }
        
        # 北大词性标注集（小写）
        pku_labels = {
            # 名词类
            'n': '名词', 'nr': '人名', 'ns': '地名', 'nt': '机构名', 'nz': '其他专名',
            'nrt': '时间词', 'nx': '外文字符', 'nw': '作品名',
            # 动词类
            'v': '动词', 'vd': '动副词', 'vn': '名动词', 'vshi': '是', 'vyou': '有',
            'vx': '形式动词', 'vi': '不及物动词', 'vl': '联系动词',
            # 形容词类
            'a': '形容词', 'ad': '副形词', 'an': '名形词', 'ag': '形语素',
            # 副词类
            'd': '副词', 'dg': '副语素',
            # 数词类
            'm': '数词', 'mq': '数量词',
            # 量词类
            'q': '量词', 'qv': '动量词', 'qt': '时量词',
            # 代词类
            'r': '代词', 'rr': '人称代词', 'rz': '指示代词', 'rzt': '时间指示代词',
            'rzs': '处所指示代词', 'rzv': '谓词性指示代词', 'ry': '疑问代词',
            'ryt': '时间疑问代词', 'rys': '处所疑问代词', 'ryv': '谓词性疑问代词',
            # 介词类
            'p': '介词', 'pba': '把', 'pbei': '被',
            # 连词类
            'c': '连词', 'cc': '并列连词',
            # 助词类
            'u': '助词', 'uzhe': '着', 'ule': '了', 'uguo': '过', 'ude1': '的/地',
            'ude2': '得', 'ude3': '的', 'usuo': '所', 'udeng': '等', 'uyy': '一样',
            'udh': '的话', 'uls': '来说', 'uzhi': '之', 'ulian': '连',
            # 语气词
            'y': '语气词',
            # 叹词
            'e': '叹词',
            # 拟声词
            'o': '拟声词',
            # 前缀
            'h': '前缀',
            # 后缀
            'k': '后缀',
            # 成语
            'i': '成语',
            # 习语
            'l': '习语',
            # 简称
            'j': '简称',
            # 区别词
            'b': '区别词',
            # 状态词
            'z': '状态词',
            # 标点符号
            'w': '标点', 'wkz': '左括号', 'wky': '右括号', 'wyz': '左引号',
            'wyy': '右引号', 'wj': '句号', 'ww': '问号', 'wt': '叹号',
            'wd': '逗号', 'wf': '分号', 'wn': '顿号', 'wm': '冒号',
            'ws': '省略号', 'wp': '破折号', 'wb': '百分号', 'wh': '单位符号',
            # 字符串
            'x': '字符串', 'xx': '非语素字', 'xu': '网址URL',
        }
        
        # 先尝试Penn Treebank（原始大小写）
        if pos_tag in ptb_labels:
            return ptb_labels[pos_tag]
        
        # 再尝试Penn Treebank（转大写）
        if pos_tag_upper in ptb_labels:
            return ptb_labels[pos_tag_upper]
        
        # 尝试北大标注集（小写）
        if pos_tag_lower in pku_labels:
            return pku_labels[pos_tag_lower]
        
        # 如果都不匹配，记录日志并返回原始标签
        logger.debug(f"未识别的词性标签: {pos_tag} (原始: {pos_tag}, 大写: {pos_tag_upper}, 小写: {pos_tag_lower})")
        return f'{pos_tag}'
    

# 创建全局实例
word_segmentation_service = WordSegmentationService()

