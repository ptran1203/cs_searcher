from django.contrib import admin
from django.urls import path, re_path
from .apis import(
    store_post,
    detail,
)

app_name = "post"

urlpatterns = [
    path('store', store_post),
    path('post/<id>', detail)
]
