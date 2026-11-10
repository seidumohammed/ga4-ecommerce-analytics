-- Product catalogue from the shop back office (secondary source), kept as text.
select
    * exclude (filename),
    filename as _source_file,
    current_timestamp as _ingested_at
from read_csv('{{ var("raw_path") }}/secondary/product_catalog.csv', header = true, all_varchar = true, filename = true)
