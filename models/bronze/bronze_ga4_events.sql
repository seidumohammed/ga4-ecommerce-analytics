-- Raw GA4 export files, loaded as they arrive. No cleaning here: duplicates, late events and placeholders stay.
select
    * exclude (filename),
    filename as _source_file,
    current_timestamp as _ingested_at
from read_parquet('{{ var("raw_path") }}/ga4/events_*.parquet', filename = true, union_by_name = true)
