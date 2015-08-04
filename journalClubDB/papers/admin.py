from django.contrib import admin

from .models import Citation

class CitationAdmin(admin.ModelAdmin):
    readonly_fields=('id',)
admin.site.register(Citation,CitationAdmin)
