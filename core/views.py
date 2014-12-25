from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test


def home(request):
    return render(request, 'home.html')


@user_passes_test(lambda u: u.is_superuser)
def clear_cache(request):
    from django.core.cache import cache
    from django.core.urlresolvers import reverse
    from django.http import HttpResponseRedirect
    from django.contrib import messages

    try:
        cache._cache.flush_all()
    except AttributeError:
        pass
    try:
        cache._cache.clear()
    except AttributeError:
        pass
    try:
        cache._expire_info.clear()
    except AttributeError:
        pass

    # django-redis
    try:
        cache.cache.clear()
    except AttributeError:
        pass

    # django-cacheops
    try:
        from cacheops.conf import redis_client

        redis_client.flushdb()
    except ImportError:
        pass

    messages.info(request, "Cache Cleared")
    try:
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    except KeyError:
        return HttpResponseRedirect(reverse("admin:index"))
    return HttpResponseRedirect(reverse("admin:index"))
