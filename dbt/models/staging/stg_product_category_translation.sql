select
    product_category_name,
    product_category_name_english
from {{ source('public', 'product_category_translation') }}
