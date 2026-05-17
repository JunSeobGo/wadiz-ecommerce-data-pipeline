from wd_silver.schemas import SCHEMAS


def test_all_schemas_have_dt():
    for schema in SCHEMAS.values():
        assert 'dt' in schema.columns
        assert schema.required_keys
        assert schema.dedup_keys
