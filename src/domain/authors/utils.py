from src.domain.authors.models import AuthorPublic
from src.infra.database.tables import Author


def convert_to_author_public(author: Author):
    return AuthorPublic(author=author.author, author_url=author.author_url)