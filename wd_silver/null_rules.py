from __future__ import annotations

COUNT_COLUMNS = {'participation_cnt', 'signature_cnt', 'content_length', 'remaining_day', 'remaining_days_at_snapshot', 'follower_cnt', 'following_cnt', 'interest_count', 'signature_count', 'total_funding_count'}
AMOUNT_COLUMNS = {'target_amount', 'total_funding_amount', 'backing_amount', 'amount', 'amount_at_wish_snapshot'}
TEXT_COLUMNS = {'title', 'raw_title', 'maker_name', 'corp_name', 'core_message', 'comment_body_cleaned', 'campaign_title', 'crawl_status', 'error_type', 'keyword_groups', 'sentiment_label', 'category_name', 'status_simplified', 'biz_model'}
BOOLEAN_COLUMNS = {'is_adult', 'has_coupon', 'is_delivery_available', 'is_global_shipping_available', 'is_purchaser', 'is_signer', 'dont_show_amount', 'is_active_user', 'has_membership', 'is_membership_user', 'is_answered', 'contains_question_mark', 'is_maker', 'is_owner', 'is_supporter', 'is_error', 'is_active_at_snapshot'}


def apply_null_rules(df):
    df = df.copy()
    for column in COUNT_COLUMNS.intersection(df.columns):
        df[column] = df[column].fillna(0)
    for column in AMOUNT_COLUMNS.intersection(df.columns):
        df[column] = df[column].fillna(0)
    for column in TEXT_COLUMNS.intersection(df.columns):
        df[column] = df[column].fillna('')
    for column in BOOLEAN_COLUMNS.intersection(df.columns):
        df[column] = df[column].fillna(False)
    return df
