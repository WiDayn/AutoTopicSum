from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional
from scipy.spatial.distance import cdist
from app.core.bert_encoder import bert_encoder
from sklearn.preprocessing import RobustScaler
from sklearn.cluster import AgglomerativeClustering, HDBSCAN

import logging
import numpy as np

logger = logging.getLogger(__name__)


class TimelineGenerator:

    DISTANCE_THRESHOLD = .6  # For clustering
    MEMBERS_IN_VALID_CLUSTER_THRESHOLD = 2  # Used by AgglomerativeClustering, filtering out clusters with fewer members than this number
    TIME_WEIGHT = 0.7

    def __init__(self, distance_threshold: Optional[float]=None, members_threshold: Optional[int]=None, time_weight: Optional[float]=None):
        self.distance_threshold = distance_threshold or self.DISTANCE_THRESHOLD
        self.members_threshold  = members_threshold or self.MEMBERS_IN_VALID_CLUSTER_THRESHOLD
        self.time_weight  = time_weight or self.TIME_WEIGHT

    def generate_timeline(self, task_id, articles: List[Dict]) -> List[Dict]:
        """分析新闻文章列表，识别关键时间点和内容。"""

        # Each info contains title, time and summary of the article (if availible)
        articles_info = [
            f'{a.get("title", "")} {a.get("summary", "")[:200]}' for a in articles
        ]

        # Embedding
        X_semantics = bert_encoder.encode_docs(articles_info)  # [N, features_num]

        # -- Convert timestamps into time features --
        timestamps = [datetime.fromisoformat(a.get('published_at', '').rstrip('Z')) for a in articles]
        # Find earliest timestamp as reference
        min_time = min(timestamps)
        # Convert each timestamp to hours since the reference point
        time_features = np.array([[(t - min_time).total_seconds() / 3600.] for t in timestamps]) # [N, 1]
        time_scaler = RobustScaler()
        time_features_scaled = time_scaler.fit_transform(time_features)
        time_features_weighted = time_features_scaled * self.time_weight
        # -----

        X_final = np.concatenate([X_semantics, time_features_weighted], axis=1)  # [N, features_num+1]

        # Clustering
        # clusterer = AgglomerativeClustering(
        #     n_clusters=None,
        #     metric='euclidean', # Has to be euclidean since time features are used
        #     linkage='average',
        #     distance_threshold=self.distance_threshold
        # )
        clusterer = HDBSCAN(
            metric='euclidean',
            min_cluster_size=2,
            cluster_selection_epsilon=self.distance_threshold,
            cluster_selection_method='eom',
            n_jobs=-1
        )
        cluster_labels = clusterer.fit_predict(X_final)

        clusters_info = defaultdict(lambda: {'a': [], 'e': [], 'i': []}) # 'a': articles, 'e': embeddings, 'i': indices
        for index, label in enumerate(cluster_labels):
            if label == -1:  # For HDBSCAN specifically, -1 means outliers
                continue
            # index: also index of articles; label: each article belongs to
            # Append the article, its embedding and index
            clusters_info[label]['a'].append(articles[index])
            clusters_info[label]['e'].append(X_final[index])
            clusters_info[label]['i'].append(index)

        timeline_nodes = []
        for label, info in clusters_info.items():
            # For AgglomerativeClustering specifically, to filter out clusters with fewer members than the threshold
            if len(info['a']) < self.members_threshold:
                continue

            # Find representative article of a cluster
            centroid = np.mean(info['e'], axis=0)  # (features_num,)
            distances = cdist(np.atleast_2d(centroid), info['e'])  # (1, features_num), (members_num, features_num)
            representative_inner_index = np.argmin(distances)
            representative_index = info['i'][representative_inner_index]
            representative_article = articles[representative_index]

            # Find earliest article of a cluster
            max_datetime_str = str(datetime.max)
            earliest_article = min(info['a'], key=lambda a: a.get('published_at', max_datetime_str))
            
            key_event_timestamp = earliest_article.get('published_at')  # TODO: Handle None
            key_event_title = representative_article.get('title', '')
            key_event_summary = representative_article.get('summary', '')

            # Collect info of articles in this cluster
            # Extract necessary info instead of the entire info['a']
            source_articles = [
                {'url': art.get('url', ''), 'source': art.get('source', ''), 'title': art.get('title', '')}
                for art in info['a']
            ]

            timeline_nodes.append({
                'timestamp': key_event_timestamp,
                'key_event': key_event_title,
                'summary': key_event_summary,
                'source_articles': source_articles,
            })
        
        timeline_nodes.sort(key=lambda node: node['timestamp'], reverse=True)
        logger.info(f'Task{task_id}: A timeline with {len(timeline_nodes)} nodes is generated.')

        return timeline_nodes


timeline_generator = TimelineGenerator()


def get_timeline_generator():
    return timeline_generator
