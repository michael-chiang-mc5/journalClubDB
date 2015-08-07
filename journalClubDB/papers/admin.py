from django.contrib import admin

from .models import Citation,Thread,Post

class PostInline(admin.TabularInline):
    model = Post
    extra = 1
    readonly_fields=('id',)
    filter_horizontal = ('upvoters','downvoters')


class ThreadAdmin(admin.ModelAdmin):
    inlines = [PostInline]
    readonly_fields=('id',)

admin.site.register(Thread,ThreadAdmin)

class CitationAdmin(admin.ModelAdmin):
    readonly_fields=('id',)
admin.site.register(Citation,CitationAdmin)
