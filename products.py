from os import urandom

def create_product_download(product):
    # If this were the real system this would be the generated product to download.
    # You'll still need to store this unique value for each order, and shouldn't change the way it is generated.
    return urandom(100_000)
