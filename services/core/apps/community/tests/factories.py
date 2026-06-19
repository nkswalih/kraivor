import uuid

import factory
from django.utils.text import slugify

from ..models import Comment, Discussion, Tag, Vote


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"tag{n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = factory.Faker("sentence")


class DiscussionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Discussion

    title = factory.Faker("sentence", nb_words=8)
    body = factory.Faker("paragraph", nb_sentences=5)
    author_id = factory.LazyFunction(uuid.uuid4)
    author_username = factory.Sequence(lambda n: f"author{n}")
    author_display_name = factory.Sequence(lambda n: f"Author {n}")


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    discussion = factory.SubFactory(DiscussionFactory)
    body = factory.Faker("paragraph")
    author_id = factory.LazyFunction(uuid.uuid4)
    author_username = factory.Sequence(lambda n: f"commenter{n}")
    author_display_name = factory.Sequence(lambda n: f"Commenter {n}")


class VoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vote

    user_id = factory.LazyFunction(uuid.uuid4)
    value = 1
