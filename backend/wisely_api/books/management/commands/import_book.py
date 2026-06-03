from django.core.management.base import BaseCommand, CommandError

from books.services import GoogleBooksError, import_book


class Command(BaseCommand):
    help = "Import book(s) from Google Books (with Open Library cover fallback) into the catalog."

    def add_arguments(self, parser):
        parser.add_argument('query', help='Search query, e.g. a title or "isbn:9780143127741".')
        parser.add_argument('--limit', type=int, default=1, help='How many top results to import.')

    def handle(self, *args, **options):
        try:
            results = import_book(options['query'], limit=options['limit'])
        except GoogleBooksError as exc:
            raise CommandError(f"Google Books request failed: {exc}")

        if not results:
            self.stdout.write(self.style.WARNING(f"No results for {options['query']!r}"))
            return

        for book, created in results:
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(
                f"{verb} '{book.title}' (isbn={book.isbn or '—'}, "
                f"audience={book.audience_score}, cover_source={book.cover_source or 'none'})"
            ))
