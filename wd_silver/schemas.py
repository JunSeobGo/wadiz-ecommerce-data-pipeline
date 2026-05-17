from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TableSchema:
    table: str
    columns: List[str]
    dtype_map: Dict[str, str]
    required_keys: List[str]
    dedup_keys: List[str]
    sort_keys: List[str]
    description: str


SCHEMAS = {
    'preorder': TableSchema(
        'preorder',
        ['campaign_id','maker_id','maker_name','corp_name','title','category_code','category_name','core_message','open_ts','close_ts','snapshot_dt','snapshot_ts','remaining_day','remaining_days_at_snapshot','achievement_rate','funding_ratio','target_amount','total_funding_amount','participation_cnt','signature_cnt','status_simplified','biz_model','is_adult','has_coupon','maker_club_grade','is_delivery_available','is_global_shipping_available','thumbnail_url','silver_processed_at','dt'],
        {'campaign_id':'Int64','maker_id':'Int64','maker_name':'string','corp_name':'string','title':'string','category_code':'string','category_name':'string','core_message':'string','open_ts':'timestamp','close_ts':'timestamp','snapshot_dt':'string','snapshot_ts':'timestamp','remaining_day':'Int64','remaining_days_at_snapshot':'Int64','achievement_rate':'float64','funding_ratio':'float64','target_amount':'Int64','total_funding_amount':'Int64','participation_cnt':'Int64','signature_cnt':'Int64','status_simplified':'string','biz_model':'string','is_adult':'boolean','has_coupon':'boolean','maker_club_grade':'string','is_delivery_available':'boolean','is_global_shipping_available':'boolean','thumbnail_url':'string','silver_processed_at':'timestamp','dt':'string'},
        ['campaign_id','snapshot_ts','dt'], ['campaign_id','snapshot_ts'], ['campaign_id','snapshot_ts'], 'Campaign performance snapshot'),
    'comments': TableSchema(
        'comments',
        ['comment_id','campaign_id','comment_type','depth','author_id_hash','comment_ts','comment_date','content_length','comment_body_cleaned','parent_comment_id','is_answered','time_to_first_answer_min','keyword_groups','sentiment_score','sentiment_label','contains_question_mark','is_maker','is_owner','is_supporter','silver_processed_at','dt'],
        {'comment_id':'string','campaign_id':'Int64','comment_type':'string','depth':'Int64','author_id_hash':'string','comment_ts':'timestamp','comment_date':'string','content_length':'Int64','comment_body_cleaned':'string','parent_comment_id':'string','is_answered':'boolean','time_to_first_answer_min':'float64','keyword_groups':'string','sentiment_score':'Int64','sentiment_label':'string','contains_question_mark':'boolean','is_maker':'boolean','is_owner':'boolean','is_supporter':'boolean','silver_processed_at':'timestamp','dt':'string'},
        ['comment_id','campaign_id','dt'], ['comment_id'], ['campaign_id','comment_ts','comment_id'], 'Comments with rule-based NLP'),
    'supporter': TableSchema(
        'supporter',
        ['user_id_hash','campaign_id','supporter_type','backing_amount','participated_at','participated_date','is_purchaser','is_signer','raw_support_type','dont_show_amount','is_active_user','has_membership','silver_processed_at','dt'],
        {'user_id_hash':'string','campaign_id':'Int64','supporter_type':'string','backing_amount':'Int64','participated_at':'timestamp','participated_date':'string','is_purchaser':'boolean','is_signer':'boolean','raw_support_type':'string','dont_show_amount':'boolean','is_active_user':'boolean','has_membership':'boolean','silver_processed_at':'timestamp','dt':'string'},
        ['user_id_hash','campaign_id','dt'], ['user_id_hash','campaign_id','participated_at','supporter_type'], ['campaign_id','participated_at','user_id_hash'], 'Supporter and purchaser rows'),
    'fundings': TableSchema(
        'fundings',
        ['user_id_hash','campaign_id','action_type','amount','funded_at','funded_date','funded_hour','funded_dow','amount_tier','campaign_title','product_type','remaining_day_at_snapshot','achievement_rate_at_snapshot','silver_processed_at','dt'],
        {'user_id_hash':'string','campaign_id':'Int64','action_type':'string','amount':'Int64','funded_at':'timestamp','funded_date':'string','funded_hour':'Int64','funded_dow':'Int64','amount_tier':'string','campaign_title':'string','product_type':'string','remaining_day_at_snapshot':'Int64','achievement_rate_at_snapshot':'float64','silver_processed_at':'timestamp','dt':'string'},
        ['user_id_hash','campaign_id','dt'], ['user_id_hash','campaign_id','funded_at','amount'], ['user_id_hash','funded_at'], 'Funding history'),
    'wishes': TableSchema(
        'wishes',
        ['user_id_hash','campaign_id','snapshot_at','snapshot_dt','wish_snapshot_date','campaign_title','maker_name','achievement_rate_at_wish_snapshot','remaining_day_at_wish_snapshot','amount_at_wish_snapshot','product_type','is_active_at_snapshot','silver_processed_at','dt'],
        {'user_id_hash':'string','campaign_id':'Int64','snapshot_at':'timestamp','snapshot_dt':'string','wish_snapshot_date':'string','campaign_title':'string','maker_name':'string','achievement_rate_at_wish_snapshot':'float64','remaining_day_at_wish_snapshot':'Int64','amount_at_wish_snapshot':'Int64','product_type':'string','is_active_at_snapshot':'boolean','silver_processed_at':'timestamp','dt':'string'},
        ['user_id_hash','campaign_id','dt'], ['user_id_hash','campaign_id','snapshot_dt'], ['user_id_hash','snapshot_dt','campaign_id'], 'Wish behavior snapshot'),
    'user_info': TableSchema(
        'user_info',
        ['user_id_hash','signature_count','total_funding_count','follower_cnt','following_cnt','interest_count','is_membership_user','user_segment','snapshot_dt','silver_processed_at','dt'],
        {'user_id_hash':'string','signature_count':'Int64','total_funding_count':'Int64','follower_cnt':'Int64','following_cnt':'Int64','interest_count':'Int64','is_membership_user':'boolean','user_segment':'string','snapshot_dt':'string','silver_processed_at':'timestamp','dt':'string'},
        ['user_id_hash','dt'], ['user_id_hash','snapshot_dt'], ['user_id_hash','snapshot_dt'], 'User profile snapshot'),
}


def get_schema(table: str) -> TableSchema:
    if table not in SCHEMAS:
        raise ValueError(f'Unsupported table: {table}. Supported tables: {sorted(SCHEMAS)}')
    return SCHEMAS[table]
