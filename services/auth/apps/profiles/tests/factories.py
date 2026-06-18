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

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.pop("user", None)
        if user is None:
            user = UserFactory()
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults=kwargs,
        )
        if not created and kwargs:
            for key, value in kwargs.items():
                setattr(profile, key, value)
            profile.save()
        return profile


class FollowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserFollow

    follower = factory.SubFactory(UserFactory)
    following = factory.SubFactory(UserFactory)
