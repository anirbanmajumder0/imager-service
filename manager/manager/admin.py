#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 nu

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from manager.models import Address, Configuration, Media, Order, Organization, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


class DefaultAdmin(admin.ModelAdmin):
    pass


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Organization, DefaultAdmin)
admin.site.register(Address, DefaultAdmin)
admin.site.register(Media, DefaultAdmin)
admin.site.register(Configuration, DefaultAdmin)
admin.site.register(Order, DefaultAdmin)
