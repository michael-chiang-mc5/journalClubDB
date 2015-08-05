from django.contrib import admin

from .models import Citation,Thread,Post

class PostInline(admin.TabularInline):
    model = Post
    extra = 1
class ThreadAdmin(admin.ModelAdmin):
    inlines = [PostInline]
admin.site.register(Thread,ThreadAdmin)


class CitationAdmin(admin.ModelAdmin):
    readonly_fields=('id',)
admin.site.register(Citation,CitationAdmin)
