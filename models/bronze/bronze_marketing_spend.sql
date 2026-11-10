-- Ad-platform spend export (secondary source). Everything is kept as text so bad values are not lost on load.
select
    * exclude (filename),
    filename as _source_file,
    current_timestamp as _ingested_at
from read_csv('{{ var("raw_path") }}/secondary/marketing_spend.csv', header = true, all_varchar = true, filename = true)
