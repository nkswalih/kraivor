import factory
from django.conf import settings
from profiles.models import Profile, UserFollow


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Sequence(lambda n: f"User {n}")


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    username = factory.Sequence(lambda n: f"user{n}")
    display_name = factory.Sequence(lambda n: f"User {n}")
    bio = factory.Faker("sentence")


class FollowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserFollow

    follower = factory.SubFactory(UserFactory)
    following = factory.SubFactory(UserFactory)
