from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from api.views import RecipeViewSet


urlpatterns = [
    path('admin/', admin.site.urls),

    path('s/<str:short_code>/',
         RecipeViewSet.as_view({'get': 'redirect_to_recipe'}),
         name='redirect-to-recipe'),

    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
