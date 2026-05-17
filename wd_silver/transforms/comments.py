from __future__ import annotations

import pandas as pd

from wd_silver.date_utils import to_timestamp
from wd_silver.pii import hash_series
from wd_silver.schemas import get_schema
from wd_silver.text_utils import clean_text, keyword_groups, sentiment_label_and_score
from wd_silver.transforms.base import coalesce_columns, enforce_schema, normalize_columns


def _flatten_raw(df: pd.DataFrame) -> pd.DataFrame:
    """comments Bronze는 {campaign_id, raw, depth, status} 구조가 많아서 raw dict를 펼칩니다."""
    if 'raw' not in df.columns:
        return df
    raw_df = pd.json_normalize(df['raw']).add_prefix('raw.')
    return pd.concat([df.reset_index(drop=True), raw_df.reset_index(drop=True)], axis=1)


def transform(df: pd.DataFrame, *, dt: str, hash_salt: str = '') -> pd.DataFrame:
    schema = get_schema('comments')
    df = normalize_columns(_flatten_raw(df))
    out = pd.DataFrame(index=df.index)

    out['comment_id'] = coalesce_columns(df, ['comment_id','commentId','id','boardId','raw.boardId'])
    out['campaign_id'] = coalesce_columns(df, ['campaign_id','campaignId','campaignid','commonId','raw.commonId','raw.campaignId'])
    out['comment_type'] = coalesce_columns(df, ['comment_type','commentType','raw.commentType','type'])
    out['depth'] = coalesce_columns(df, ['depth','commentDepth','raw.depth'])
    author_id = coalesce_columns(df, ['author_id','authorId','user_id','userId','encUserId','raw.encUserId','raw.userFollow.userId'])
    out['author_id_hash'] = hash_series(author_id, salt=hash_salt).astype('string')
    out['comment_ts'] = to_timestamp(coalesce_columns(df, ['comment_ts','createdAt','created_at','registeredAt','whenCreated','raw.whenCreated']))
    out['comment_date'] = out['comment_ts'].dt.strftime('%Y%m%d')
    out['comment_body_cleaned'] = coalesce_columns(df, ['comment_body','body','content','text','comment','raw.body']).apply(clean_text)
    out['content_length'] = out['comment_body_cleaned'].str.len()
    out['parent_comment_id'] = coalesce_columns(df, ['parent_comment_id','parentCommentId','parentBoardId','raw.parentBoardId'])
    out['is_answered'] = coalesce_columns(df, ['is_answered','answered','isAnswered','hasReply','raw.hasReply'])
    out['time_to_first_answer_min'] = coalesce_columns(df, ['time_to_first_answer_min'])
    out['keyword_groups'] = out['comment_body_cleaned'].apply(keyword_groups)
    sentiment = out['comment_body_cleaned'].apply(sentiment_label_and_score)
    out['sentiment_label'] = sentiment.apply(lambda x: x[0])
    out['sentiment_score'] = sentiment.apply(lambda x: x[1])
    out['contains_question_mark'] = out['comment_body_cleaned'].str.contains(r'[?？]|나요|까요|문의', regex=True, na=False)
    out['is_maker'] = coalesce_columns(df, ['is_maker','isMaker','maker','raw.maker'])
    out['is_owner'] = coalesce_columns(df, ['is_owner','isOwner','owner','raw.owner'])
    out['is_supporter'] = coalesce_columns(df, ['is_supporter','isSupporter','support','raw.support'])
    return enforce_schema(out, schema, dt)
