"""Build affiliate purchase links for books (Bookshop.org + Amazon Associates).

Links are generated from each book's ISBN plus your account tags in settings, so every
imported book gets buy-links automatically — no manual link entry. Outbound clicks are
tracked via the /api/books/{id}/buy/ redirect, which logs an Event then forwards here.
"""
from django.conf import settings

BOOKSHOP = 'bookshop'
AMAZON = 'amazon'
PROVIDERS = (BOOKSHOP, AMAZON)


def bookshop_url(book):
    isbn = book.isbn or book.isbn_10
    if not isbn:
        return ''
    affiliate_id = getattr(settings, 'BOOKSHOP_AFFILIATE_ID', '')
    if affiliate_id:
        return f"https://bookshop.org/a/{affiliate_id}/{isbn}"
    return f"https://bookshop.org/books?keywords={isbn}"


def amazon_url(book):
    tag = getattr(settings, 'AMAZON_ASSOCIATE_TAG', '')
    if book.isbn_10:  # Amazon uses the ISBN-10 as the ASIN for most books
        base = f"https://www.amazon.com/dp/{book.isbn_10}"
        return f"{base}?tag={tag}" if tag else base
    if book.isbn:
        base = f"https://www.amazon.com/s?k={book.isbn}"
        return f"{base}&tag={tag}" if tag else base
    return ''


_BUILDERS = {BOOKSHOP: bookshop_url, AMAZON: amazon_url}


def affiliate_url(book, provider):
    """Return the retailer URL for a book + provider, or '' if it can't be built."""
    builder = _BUILDERS.get(provider)
    return builder(book) if builder else ''
