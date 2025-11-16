"""BERT编码器 - 媒体关键词相似度聚合"""
import logging
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from difflib import SequenceMatcher
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from config import Config

logger = logging.getLogger(__name__)

# 尝试导入 sentence-transformers，如果失败则使用字符级别相似度
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers 未安装，将使用字符级别相似度计算。建议安装：pip install sentence-transformers")


class BERTEncoder:
    """BERT编码器 - 将相似的关键词聚合为统一的关键词"""
    
    # 相似度阈值
    SIMILARITY_THRESHOLD = 0.7
    
    # 中文语义相似度模型（懒加载）
    _semantic_model = None
    
    # 特殊规则映射（优先级最高）
    SPECIAL_RULES = {
        'location': {
            # 地理位置聚合规则
            '中国': ['中国大陆', '中国', '中国内地', '内地'],
            '美国': ['美国', 'USA', 'United States'],
            '英国': ['英国', 'UK', 'United Kingdom'],
            '全球': ['全球', '国际', '世界', '全世界'],
        },
        'political_stance': {
            # 政治立场聚合规则
            '官方': ['官方立场', '官方', '政府立场', '官方媒体'],
            '中立': ['中立', '中立立场', '中间立场', '中性'],
            '左倾': ['左倾', '左翼', '进步主义'],
            '右倾': ['右倾', '右翼', '保守主义'],
            '自由主义': ['自由主义', '自由派', '自由市场'],
        },
        'ownership': {
            # 所有制聚合规则
            '国有': ['国有', '国有企业', '国有控股', '公有制', '政府所有'],
            '民营': ['民营', '民营企业', '私营', '私营企业', '私人所有'],
            '外资': ['外资', '外资控股', '外国资本'],
            '混合': ['混合所有制', '混合', '多元'],
        },
        'category': {
            # 媒体类别聚合规则
            '新闻媒体': ['新闻媒体', '新闻机构', '新闻门户', '新闻网站'],
            '科技媒体': ['科技媒体', '科技博客', '科技资讯', '科技门户'],
            '财经媒体': ['财经媒体', '财经门户', '财经网站', '财经新闻'],
        }
    }
    
    def __init__(self, similarity_threshold: Optional[float] = None):
        """
        初始化BERT编码器
        
        Args:
            similarity_threshold: 相似度阈值（0-1之间），默认0.7
        """
        self.similarity_threshold = similarity_threshold or self.SIMILARITY_THRESHOLD
        # 编码映射记录：{字段名: {原始关键词: 编码后关键词}}
        self.encoding_mapping: Dict[str, Dict[str, str]] = {}
        # 最后一次聚类的统计信息
        self.last_clustering_stats: Optional[Dict] = None
        # 当前聚类映射（临时变量）
        self._current_cluster_mapping: Dict[str, str] = {}
        # 记录文件路径
        self.record_file = Config.BERT_ENCODING_RECORD_FILE
        # 是否使用语义相似度
        self._use_semantic_similarity = SENTENCE_TRANSFORMERS_AVAILABLE
        # 加载历史记录
        self._load_record()
        logger.info(f"BERT编码器初始化，相似度阈值: {self.similarity_threshold}, 语义相似度: {'启用' if self._use_semantic_similarity else '禁用（使用字符级别相似度）'}")
    
    def _get_semantic_model(self):
        """懒加载中文语义相似度模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
        
        if BERTEncoder._semantic_model is None:
            try:
                # 使用多语言模型，支持中文
                # paraphrase-multilingual-MiniLM-L12-v2 是一个轻量级多语言模型
                logger.info("正在加载中文语义相似度模型...")
                BERTEncoder._semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logger.info("中文语义相似度模型加载成功")
            except Exception as e:
                logger.warning(f"加载语义相似度模型失败: {str(e)}，将使用字符级别相似度")
                BERTEncoder._semantic_model = None  # 标记为加载失败，避免重复尝试
        return BERTEncoder._semantic_model
    
    def encode_media_info(self, media_info: Dict) -> Dict:
        """
        编码媒体信息，聚合相似关键词
        
        Args:
            media_info: 媒体信息字典
            
        Returns:
            编码后的媒体信息字典
        """
        encoded_info = media_info.copy()
        
        # 需要编码的字段
        fields_to_encode = [
            'ownership', 'funding', 'political_stance',
            'content_domain', 'location', 'target_audience', 'category'
        ]
        
        for field in fields_to_encode:
            if field in encoded_info and encoded_info[field]:
                original_value = encoded_info[field]
                encoded_value = self.encode_field(field, original_value)
                encoded_info[field] = encoded_value
                
                if original_value != encoded_value:
                    logger.debug(
                        f"字段 {field} 编码: '{original_value}' -> '{encoded_value}'"
                    )
        
        return encoded_info
    
    def encode_field(self, field_name: str, value: str) -> str:
        """
        编码单个字段的关键词
        
        Args:
            field_name: 字段名
            value: 字段值（用/分隔的关键词）
            
        Returns:
            编码后的字段值
        """
        if not value or not value.strip():
            return value
        
        # 分割关键词（保存原始关键词）
        original_keywords = [k.strip() for k in value.split('/') if k.strip()]
        
        if not original_keywords:
            return value
        
        # 初始化字段映射（如果不存在）
        if field_name not in self.encoding_mapping:
            self.encoding_mapping[field_name] = {}
        
        # 检查是否有全局聚类结果（在batch_encode中预先计算的）
        global_cluster_stats = {}
        has_global_clustering = False
        if (self.last_clustering_stats and 
            'fields' in self.last_clustering_stats and 
            field_name in self.last_clustering_stats['fields']):
            global_cluster_stats = self.last_clustering_stats['fields'][field_name]
            # 如果有全局相似性矩阵，说明已经进行了全局聚类
            has_global_clustering = 'similarity_matrix' in global_cluster_stats
        
        # 清空当前字段的聚类映射（避免字段间冲突）
        self._current_cluster_mapping = {}
        
        # 建立原始关键词到规则处理后关键词的映射
        orig_to_rule_mapping = {}
        keywords_after_rules = self._apply_special_rules(field_name, original_keywords.copy())
        
        for orig, after_rule in zip(original_keywords, keywords_after_rules):
            orig_to_rule_mapping[orig] = after_rule
            if orig != after_rule:
                # 记录规则映射
                self.encoding_mapping[field_name][orig] = after_rule
        
        # 如果已经有全局聚类结果，使用全局聚类映射；否则进行局部聚类
        if has_global_clustering and global_cluster_stats.get('clusters'):
            # 使用全局聚类结果：从聚类详情中构建映射关系
            cluster_rep_map = {}
            for cluster_info in global_cluster_stats.get('clusters', []):
                rep = cluster_info.get('representative')
                members = cluster_info.get('members', [])
                for member in members:
                    cluster_rep_map[member] = rep
                # 代表词映射到自己
                cluster_rep_map[rep] = rep
            
            # 对于不在任何聚类中的关键词，它们映射到自己
            global_keywords = global_cluster_stats.get('similarity_matrix', {}).get('keywords', [])
            for kw in global_keywords:
                if kw not in cluster_rep_map:
                    cluster_rep_map[kw] = kw
            
            # 应用聚类映射
            clustered_keywords = []
            for kw in keywords_after_rules:
                rep = cluster_rep_map.get(kw, kw)
                if rep not in clustered_keywords:
                    clustered_keywords.append(rep)
            keywords = clustered_keywords
        else:
            # 没有全局聚类结果，进行局部聚类（会在内部记录映射关系到 _current_cluster_mapping）
            keywords = self._cluster_by_similarity(keywords_after_rules, field_name=None)  # 不保存统计信息，避免覆盖全局统计
            # 获取聚类映射关系（这是当前字段的聚类映射）
            cluster_rep_map = self._current_cluster_mapping.copy()
        
        # 记录最终映射：原始关键词 -> 最终编码结果
        for orig_keyword in original_keywords:
            # 找到原始关键词经过规则处理后的结果
            rule_result = orig_to_rule_mapping.get(orig_keyword, orig_keyword)
            # 找到规则结果对应的聚类代表词
            final_result = cluster_rep_map.get(rule_result, rule_result)
            # 记录映射（如果发生变化）
            if orig_keyword != final_result:
                self.encoding_mapping[field_name][orig_keyword] = final_result
        
        # 去重并保持顺序
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return '/'.join(unique_keywords)
    
    def _apply_special_rules(self, field_name: str, keywords: List[str]) -> List[str]:
        """
        应用特殊规则映射
        
        Args:
            field_name: 字段名
            keywords: 关键词列表
            
        Returns:
            应用规则后的关键词列表
        """
        if field_name not in self.SPECIAL_RULES:
            return keywords
        
        rules = self.SPECIAL_RULES[field_name]
        result = []
        
        for keyword in keywords:
            matched = False
            # 检查是否匹配任何规则
            for standard_term, variants in rules.items():
                # 检查精确匹配或包含关系
                if keyword == standard_term or keyword in variants:
                    result.append(standard_term)
                    matched = True
                    break
                # 检查关键词是否包含标准术语或其变体
                elif any(variant in keyword or keyword in variant 
                        for variant in variants + [standard_term]):
                    result.append(standard_term)
                    matched = True
                    break
            
            if not matched:
                result.append(keyword)
        
        return result
    
    def _cluster_by_similarity(self, keywords: List[str], field_name: str = None) -> List[str]:
        """
        基于相似度聚类关键词（使用层次聚类算法）
        
        Args:
            keywords: 关键词列表
            field_name: 字段名（用于记录聚类统计）
            
        Returns:
            聚类后的关键词列表（使用代表词）
        """
        if len(keywords) <= 1:
            # 即使只有一个关键词，也要设置映射关系
            if keywords:
                self._current_cluster_mapping[keywords[0]] = keywords[0]
                
                # 保存相似性矩阵（只有一个元素）
                if field_name:
                    similarity_matrix = np.array([[1.0]]) if len(keywords) == 1 else np.array([])
                    similarity_matrix_list = similarity_matrix.tolist() if len(keywords) == 1 else []
                    
                    if not self.last_clustering_stats:
                        self.last_clustering_stats = {
                            'timestamp': datetime.now().isoformat(),
                            'fields': {}
                        }
                    if 'fields' not in self.last_clustering_stats:
                        self.last_clustering_stats['fields'] = {}
                    
                    self.last_clustering_stats['fields'][field_name] = {
                        'before_count': len(keywords),
                        'after_count': len(keywords),
                        'reduction': 0,
                        'reduction_rate': 0.0,
                        'clusters': [],
                        'total_clusters': len(keywords),
                        'clustered_keywords': 0,
                        'similarity_matrix': {
                            'keywords': keywords,
                            'matrix': similarity_matrix_list
                        }
                    }
                    self.last_clustering_stats['timestamp'] = datetime.now().isoformat()
            return keywords
        
        # 批量计算相似度矩阵
        similarity_matrix = self._calculate_similarity_matrix_batch(keywords)
        
        # 将相似度转换为距离（距离 = 1 - 相似度）
        distance_matrix = 1.0 - similarity_matrix
        
        # 使用层次聚类算法
        # distance_threshold 设置为 1 - similarity_threshold
        # 即如果相似度 >= similarity_threshold，则距离 <= (1 - similarity_threshold)
        distance_threshold = 1.0 - self.similarity_threshold
        
        # 使用 AgglomerativeClustering 进行聚类
        clustering = AgglomerativeClustering(
            n_clusters=None,  # 不指定聚类数量，使用距离阈值
            distance_threshold=distance_threshold,
            metric='precomputed',  # 使用预计算的距离矩阵
            linkage='average'  # 使用平均链接
        )
        
        try:
            cluster_labels = clustering.fit_predict(distance_matrix)
        except Exception as e:
            logger.warning(f"聚类算法执行失败: {str(e)}，回退到贪心方法")
            return self._cluster_by_similarity_greedy(keywords, field_name=field_name)
        
        # 根据聚类标签分组
        clusters_dict = {}
        keyword_to_label = {}  # 记录每个关键词的聚类标签
        for idx, label in enumerate(cluster_labels):
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(keywords[idx])
            keyword_to_label[keywords[idx]] = label
        
        # 为每个聚类选择代表词，并构建映射关系
        representatives = []
        cluster_details = []  # 记录聚类详情
        label_to_representative = {}  # 聚类标签到代表词的映射
        
        for label, cluster in clusters_dict.items():
            representative = self._choose_representative(cluster)
            representatives.append(representative)
            label_to_representative[label] = representative
            
            # 记录聚类详情
            if len(cluster) > 1:  # 只记录有多个成员的聚类
                cluster_details.append({
                    'representative': representative,
                    'members': cluster,
                    'size': len(cluster)
                })
        
        # 构建关键词到代表词的映射
        keyword_to_representative = {}
        for keyword in keywords:
            label = keyword_to_label[keyword]
            representative = label_to_representative[label]
            keyword_to_representative[keyword] = representative
        
        # 将映射关系存储到实例变量，供 encode_field 使用
        if not hasattr(self, '_current_cluster_mapping'):
            self._current_cluster_mapping = {}
        # 更新当前聚类映射（追加而不是覆盖，因为可能有多个字段）
        self._current_cluster_mapping.update(keyword_to_representative)
        
        # 记录聚类统计信息
        if field_name:
            if not self.last_clustering_stats:
                self.last_clustering_stats = {
                    'timestamp': datetime.now().isoformat(),
                    'fields': {}
                }
            if 'fields' not in self.last_clustering_stats:
                self.last_clustering_stats['fields'] = {}
            
            # 将相似性矩阵转换为列表（numpy数组不能直接JSON序列化）
            similarity_matrix_list = similarity_matrix.tolist()
            
            # 记录聚类详情（before_count 和 after_count 会在 batch_encode 中统一更新）
            self.last_clustering_stats['fields'][field_name] = {
                'before_count': len(keywords),  # 临时值，会在 batch_encode 中被覆盖
                'after_count': len(representatives),  # 临时值，会在 batch_encode 中被覆盖
                'reduction': 0,  # 临时值，会在 batch_encode 中被覆盖
                'reduction_rate': 0.0,  # 临时值，会在 batch_encode 中被覆盖
                'clusters': cluster_details,  # 保留聚类详情
                'total_clusters': len(clusters_dict),
                'clustered_keywords': len(keywords) - len(representatives),
                'similarity_matrix': {
                    'keywords': keywords,  # 关键词列表（顺序与矩阵对应）
                    'matrix': similarity_matrix_list  # 相似度矩阵（二维数组）
                }
            }
            self.last_clustering_stats['timestamp'] = datetime.now().isoformat()
        
        logger.debug(
            f"聚类完成: {len(keywords)} 个关键词聚类为 {len(representatives)} 个"
        )
        
        return representatives
    
    def _cluster_by_similarity_greedy(self, keywords: List[str], field_name: str = None) -> List[str]:
        """
        基于相似度的贪心聚类方法（备用方法）
        
        Args:
            keywords: 关键词列表
            field_name: 字段名（用于记录聚类统计）
            
        Returns:
            聚类后的关键词列表（使用代表词）
        """
        if len(keywords) <= 1:
            # 即使只有一个关键词，也要设置映射关系
            if keywords:
                if not hasattr(self, '_current_cluster_mapping'):
                    self._current_cluster_mapping = {}
                self._current_cluster_mapping[keywords[0]] = keywords[0]
                
                # 保存相似性矩阵（只有一个元素）
                if field_name:
                    similarity_matrix = np.array([[1.0]]) if len(keywords) == 1 else np.array([])
                    similarity_matrix_list = similarity_matrix.tolist() if len(keywords) == 1 else []
                    
                    if not self.last_clustering_stats:
                        self.last_clustering_stats = {
                            'timestamp': datetime.now().isoformat(),
                            'fields': {}
                        }
                    if 'fields' not in self.last_clustering_stats:
                        self.last_clustering_stats['fields'] = {}
                    
                    self.last_clustering_stats['fields'][field_name] = {
                        'before_count': len(keywords),
                        'after_count': len(keywords),
                        'reduction': 0,
                        'reduction_rate': 0.0,
                        'clusters': [],
                        'total_clusters': len(keywords),
                        'clustered_keywords': 0,
                        'similarity_matrix': {
                            'keywords': keywords,
                            'matrix': similarity_matrix_list
                        }
                    }
                    self.last_clustering_stats['timestamp'] = datetime.now().isoformat()
            return keywords
        
        # 创建聚类
        clusters = []
        cluster_mapping = {}  # 记录每个关键词到代表词的映射
        unassigned = keywords.copy()
        
        while unassigned:
            # 取第一个未分配的关键词作为聚类中心
            center = unassigned.pop(0)
            cluster = [center]
            
            # 查找相似的关键词
            remaining = []
            for keyword in unassigned:
                similarity = self._calculate_similarity(center, keyword)
                if similarity >= self.similarity_threshold:
                    cluster.append(keyword)
                else:
                    remaining.append(keyword)
            
            # 选择最合适的代表词（通常是较短的）
            representative = self._choose_representative(cluster)
            clusters.append(representative)
            
            # 记录映射关系
            for member in cluster:
                cluster_mapping[member] = representative
            
            unassigned = remaining
        
        # 更新当前聚类映射
        if not hasattr(self, '_current_cluster_mapping'):
            self._current_cluster_mapping = {}
        self._current_cluster_mapping.update(cluster_mapping)
        
        # 批量计算相似性矩阵（贪心方法也需要保存，使用批量计算以减少日志）
        similarity_matrix = self._calculate_similarity_matrix_batch(keywords)
        
        # 将相似性矩阵转换为列表
        similarity_matrix_list = similarity_matrix.tolist()
        
        # 记录聚类统计信息（简化版）
        if field_name:
            cluster_details = []
            # 重建聚类详情（简化处理）
            cluster_groups = {}
            for keyword, rep in cluster_mapping.items():
                if rep not in cluster_groups:
                    cluster_groups[rep] = []
                cluster_groups[rep].append(keyword)
            
            for rep, members in cluster_groups.items():
                if len(members) > 1:
                    cluster_details.append({
                        'representative': rep,
                        'members': members,
                        'size': len(members)
                    })
            
            if not self.last_clustering_stats:
                self.last_clustering_stats = {
                    'timestamp': datetime.now().isoformat(),
                    'fields': {}
                }
            if 'fields' not in self.last_clustering_stats:
                self.last_clustering_stats['fields'] = {}
            
            # 记录聚类详情（before_count 和 after_count 会在 batch_encode 中统一更新）
            self.last_clustering_stats['fields'][field_name] = {
                'before_count': len(keywords),  # 临时值，会在 batch_encode 中被覆盖
                'after_count': len(clusters),  # 临时值，会在 batch_encode 中被覆盖
                'reduction': 0,  # 临时值，会在 batch_encode 中被覆盖
                'reduction_rate': 0.0,  # 临时值，会在 batch_encode 中被覆盖
                'clusters': cluster_details,  # 保留聚类详情
                'total_clusters': len(clusters),
                'clustered_keywords': len(keywords) - len(clusters),
                'similarity_matrix': {
                    'keywords': keywords,
                    'matrix': similarity_matrix_list
                }
            }
            self.last_clustering_stats['timestamp'] = datetime.now().isoformat()
        
        return clusters
    
    def _calculate_similarity_matrix_batch(self, keywords: List[str]) -> np.ndarray:
        """
        批量计算关键词相似度矩阵（优化性能，减少日志输出）
        
        Args:
            keywords: 关键词列表
            
        Returns:
            相似度矩阵 (n x n numpy array)
        """
        n = len(keywords)
        similarity_matrix = np.zeros((n, n))
        
        # 完全匹配和包含关系的快速检查
        for i in range(n):
            similarity_matrix[i][i] = 1.0
            for j in range(i + 1, n):
                # 完全匹配
                if keywords[i] == keywords[j]:
                    similarity_matrix[i][j] = 1.0
                    similarity_matrix[j][i] = 1.0
                    continue
                
                # 包含关系检查
                if keywords[i] in keywords[j] or keywords[j] in keywords[i]:
                    shorter = min(len(keywords[i]), len(keywords[j]))
                    longer = max(len(keywords[i]), len(keywords[j]))
                    ratio = shorter / longer
                    if ratio > 0.5:
                        similarity = min(0.9, 0.7 + ratio * 0.2)
                    else:
                        similarity = ratio
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
                    continue
        
        # 尝试使用语义相似度模型批量计算
        semantic_model = self._get_semantic_model()
        if semantic_model:
            try:
                # 批量编码所有关键词（一次性处理，减少日志输出）
                # 设置环境变量来抑制进度条
                old_env = os.environ.get('TRANSFORMERS_VERBOSITY', None)
                os.environ['TRANSFORMERS_VERBOSITY'] = 'error'  # 抑制进度条
                
                try:
                    # 批量编码
                    embeddings = semantic_model.encode(
                        keywords, 
                        convert_to_numpy=True,
                        show_progress_bar=False,  # 禁用进度条
                        batch_size=32
                    )
                    
                    # 批量计算余弦相似度矩阵
                    # 归一化向量
                    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                    norms[norms == 0] = 1  # 避免除零
                    embeddings_normalized = embeddings / norms
                    
                    # 计算余弦相似度矩阵 (embeddings_normalized @ embeddings_normalized.T)
                    semantic_similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
                    
                    # 确保值在 [0, 1] 范围内
                    semantic_similarity_matrix = np.clip(semantic_similarity_matrix, 0.0, 1.0)
                    
                    # 对于已经计算过的完全匹配和包含关系，保留原值；否则使用语义相似度
                    for i in range(n):
                        for j in range(i + 1, n):
                            # 如果相似度矩阵中还没有值（即不是完全匹配也不是包含关系），使用语义相似度
                            # 或者语义相似度更高，则使用语义相似度
                            if similarity_matrix[i][j] == 0.0 or semantic_similarity_matrix[i][j] > similarity_matrix[i][j]:
                                similarity_matrix[i][j] = float(semantic_similarity_matrix[i][j])
                                similarity_matrix[j][i] = float(semantic_similarity_matrix[i][j])
                
                finally:
                    # 恢复环境变量
                    if old_env is None:
                        os.environ.pop('TRANSFORMERS_VERBOSITY', None)
                    else:
                        os.environ['TRANSFORMERS_VERBOSITY'] = old_env
                        
            except Exception as e:
                logger.debug(f"批量语义相似度计算失败: {str(e)}，使用字符级别相似度")
                # 继续使用字符级别相似度补充
        
        # 对于还没有计算相似度的位置，使用字符级别相似度
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i][j] == 0.0:
                    # 使用字符级别相似度
                    similarity = SequenceMatcher(None, keywords[i], keywords[j]).ratio()
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
        
        return similarity_matrix
    
    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """
        计算两个关键词的相似度（优先使用语义相似度，回退到字符级别相似度）
        
        Args:
            word1: 关键词1
            word2: 关键词2
            
        Returns:
            相似度分数（0-1）
        """
        # 完全匹配
        if word1 == word2:
            return 1.0
        
        # 包含关系（一个包含另一个）- 对于中文，包含关系通常表示高相似度
        if word1 in word2 or word2 in word1:
            # 计算包含比例，但给予更高的基础分数（因为中文中"官方"包含在"官方立场"中表示语义相关）
            shorter = min(len(word1), len(word2))
            longer = max(len(word1), len(word2))
            ratio = shorter / longer
            # 如果包含比例较高（>0.5），给予较高的相似度分数
            if ratio > 0.5:
                return min(0.9, 0.7 + ratio * 0.2)  # 范围在0.7-0.9之间
            return ratio
        
        # 尝试使用语义相似度模型
        semantic_model = self._get_semantic_model()
        if semantic_model:
            try:
                # 计算语义相似度（余弦相似度）
                embeddings = semantic_model.encode([word1, word2], convert_to_numpy=True)
                # 计算余弦相似度
                similarity = np.dot(embeddings[0], embeddings[1]) / (
                    np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
                )
                # 将余弦相似度（范围通常为-1到1）归一化到0-1范围
                # 由于embedding通常相似度在0-1之间，这里直接使用，如果小于0则设为0
                semantic_similarity = max(0.0, similarity)
                return float(semantic_similarity)
            except Exception as e:
                logger.debug(f"语义相似度计算失败: {str(e)}，使用字符级别相似度")
        
        # 回退到字符级别相似度（使用序列匹配）
        similarity = SequenceMatcher(None, word1, word2).ratio()
        return similarity
    
    def _choose_representative(self, cluster: List[str]) -> str:
        """
        从聚类中选择代表词
        
        Args:
            cluster: 聚类中的关键词列表
            
        Returns:
            代表词
        """
        if len(cluster) == 1:
            return cluster[0]
        
        # 优先选择较短的词（通常更简洁）
        # 如果长度相同，选择第一个
        cluster_sorted = sorted(cluster, key=lambda x: (len(x), x))
        return cluster_sorted[0]
    
    def batch_encode_media(self, media_info_dict: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        批量编码多个媒体的信息
        
        Args:
            media_info_dict: 媒体信息字典 {媒体名: 媒体信息}
            
        Returns:
            编码后的媒体信息字典
        """
        # 清空当前聚类映射
        self._current_cluster_mapping = {}
        
        # 第一步：收集所有媒体的原始关键词（编码前）
        fields_to_encode = [
            'ownership', 'funding', 'political_stance',
            'content_domain', 'location', 'target_audience', 'category'
        ]
        
        # 收集每个字段的所有原始唯一关键词
        all_original_keywords = {field: set() for field in fields_to_encode}
        
        for media_name, media_info in media_info_dict.items():
            for field in fields_to_encode:
                if field in media_info and media_info[field]:
                    # 分割用 / 分隔的关键词
                    keywords = [k.strip() for k in media_info[field].split('/') if k.strip()]
                    all_original_keywords[field].update(keywords)
        
        # 初始化统计信息
        if not self.last_clustering_stats:
            self.last_clustering_stats = {
                'timestamp': datetime.now().isoformat(),
                'fields': {}
            }
        self.last_clustering_stats['fields'] = {}
        
        # 第二步：对每个字段的所有关键词进行全局聚类（计算相似性矩阵）
        # 将set转换为list并排序，确保顺序一致
        all_keywords_list = {}
        for field in fields_to_encode:
            keywords_list = sorted(list(all_original_keywords[field]))
            all_keywords_list[field] = keywords_list
            
            if keywords_list:
                # 对全局关键词进行聚类分析（这会计算并保存相似性矩阵）
                logger.info(f"对字段 {field} 的 {len(keywords_list)} 个全局关键词进行聚类分析")
                # 应用特殊规则
                keywords_after_rules = self._apply_special_rules(field, keywords_list.copy())
                # 全局聚类（会保存相似性矩阵）
                _ = self._cluster_by_similarity(keywords_after_rules, field_name=field)
        
        # 第三步：编码每个媒体，使用全局聚类结果
        encoded_dict = {}
        
        for media_name, media_info in media_info_dict.items():
            encoded_info = self.encode_media_info(media_info)
            encoded_dict[media_name] = encoded_info
        
        # 第三步：收集所有媒体编码后的唯一关键词
        all_encoded_keywords = {field: set() for field in fields_to_encode}
        
        for media_name, encoded_info in encoded_dict.items():
            for field in fields_to_encode:
                if field in encoded_info and encoded_info[field]:
                    # 分割用 / 分隔的关键词
                    keywords = [k.strip() for k in encoded_info[field].split('/') if k.strip()]
                    all_encoded_keywords[field].update(keywords)
        
        # 第四步：更新统计信息（使用所有媒体的唯一关键词数量）
        for field in fields_to_encode:
            original_count = len(all_original_keywords[field])
            encoded_count = len(all_encoded_keywords[field])
            
            if original_count > 0 or encoded_count > 0:
                # 如果字段有统计信息（说明进行了聚类），则更新统计数字，但保留相似性矩阵
                if field in self.last_clustering_stats['fields']:
                    field_stats = self.last_clustering_stats['fields'][field]
                    # 保存相似性矩阵（如果存在）
                    similarity_matrix = field_stats.get('similarity_matrix')
                    # 更新统计数字
                    field_stats['before_count'] = original_count
                    field_stats['after_count'] = encoded_count
                    field_stats['reduction'] = original_count - encoded_count
                    field_stats['reduction_rate'] = (
                        (original_count - encoded_count) / original_count * 100
                        if original_count > 0 else 0
                    )
                    # 恢复相似性矩阵（如果之前存在）
                    if similarity_matrix:
                        field_stats['similarity_matrix'] = similarity_matrix
                else:
                    # 如果没有统计信息，创建一个（表示没有发生聚类）
                    self.last_clustering_stats['fields'][field] = {
                        'before_count': original_count,
                        'after_count': encoded_count,
                        'reduction': original_count - encoded_count,
                        'reduction_rate': (
                            (original_count - encoded_count) / original_count * 100
                            if original_count > 0 else 0
                        ),
                        'clusters': [],
                        'total_clusters': encoded_count,
                        'clustered_keywords': 0
                    }
        
        # 保存编码记录和聚类统计
        self._save_record()
        
        logger.info(f"批量编码完成，共处理 {len(encoded_dict)} 个媒体")
        return encoded_dict
    
    def encode_docs(self, docs: List[str]):
        semantic_model = self._get_semantic_model()
        if semantic_model is None:
            pass  # TODO TF-IDF?
            embeddings = np.random.rand(len(docs), 10)
        else:
            # (N, feature_nums)
            embeddings = semantic_model.encode(docs, normalize_embeddings=True, convert_to_numpy=True)
        return embeddings


    def get_statistics(self, media_info_dict: Dict[str, Dict]) -> Dict:
        """
        获取编码前后的统计信息
        
        Args:
            media_info_dict: 媒体信息字典
            
        Returns:
            统计信息字典
        """
        original_keywords = {}
        encoded_dict = self.batch_encode_media(media_info_dict)
        
        fields = ['ownership', 'funding', 'political_stance',
                 'content_domain', 'location', 'target_audience', 'category']
        
        stats = {}
        for field in fields:
            original_set = set()
            encoded_set = set()
            
            for media_info in media_info_dict.values():
                if field in media_info and media_info[field]:
                    keywords = [k.strip() for k in media_info[field].split('/')]
                    original_set.update(keywords)
            
            for media_info in encoded_dict.values():
                if field in media_info and media_info[field]:
                    keywords = [k.strip() for k in media_info[field].split('/')]
                    encoded_set.update(keywords)
            
            stats[field] = {
                'original_count': len(original_set),
                'encoded_count': len(encoded_set),
                'reduction': len(original_set) - len(encoded_set),
                'reduction_rate': (len(original_set) - len(encoded_set)) / len(original_set) * 100 if original_set else 0
            }
        
        return stats
    
    def _load_record(self):
        """从文件加载编码记录"""
        try:
            if os.path.exists(self.record_file):
                with open(self.record_file, 'r', encoding='utf-8') as f:
                    record_data = json.load(f)
                    self.encoding_mapping = record_data.get('encoding_mapping', {})
                    self.last_clustering_stats = record_data.get('last_clustering_stats', None)
                    logger.info(f"已加载BERT编码记录: {self.record_file}")
            else:
                logger.info("BERT编码记录文件不存在，将创建新记录")
                self.encoding_mapping = {}
                self.last_clustering_stats = None
        except Exception as e:
            logger.error(f"加载BERT编码记录失败: {str(e)}")
            self.encoding_mapping = {}
            self.last_clustering_stats = None
    
    def _save_record(self):
        """保存编码记录到文件"""
        try:
            # 确保目录存在
            record_dir = os.path.dirname(self.record_file)
            if record_dir and not os.path.exists(record_dir):
                os.makedirs(record_dir)
            
            record_data = {
                'encoding_mapping': self.encoding_mapping,
                'last_clustering_stats': self.last_clustering_stats,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.record_file, 'w', encoding='utf-8') as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存BERT编码记录: {self.record_file}")
        except Exception as e:
            logger.error(f"保存BERT编码记录失败: {str(e)}")
    
    def get_encoding_record(self) -> Dict:
        """
        获取编码记录信息（供API调用）
        
        Returns:
            包含编码映射和聚类统计的字典
        """
        return {
            'encoding_mapping': self.encoding_mapping,
            'last_clustering_stats': self.last_clustering_stats,
            'similarity_threshold': self.similarity_threshold
        }


# 全局编码器实例
bert_encoder = BERTEncoder()
