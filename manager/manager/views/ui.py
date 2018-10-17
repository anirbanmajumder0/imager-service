#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging

from django import forms
from django.http import Http404
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required

from manager.models import Address, Media, Configuration

logger = logging.getLogger(__name__)


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["name", "recipient", "email", "phone", "address", "country"]

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization")
        super().__init__(*args, **kwargs)
        self.organization = organization

    def phone_clean(self):
        try:
            cleaned_phone = AddressForm.clean_phone(self.cleaned_data.get("phone"))
        except Exception as exp:
            logger.error(exp)
            raise forms.ValidationError("Invalid Phone Number", code="invalid")

        return cleaned_phone

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        instance.organization = self.organization
        instance.save()
        return instance

    @classmethod
    def success_message(cls, res):
        return "Successfuly created Address <em>{}</em>".format(res)


class OrderForm(forms.Form):
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization")
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["config"].choices = Configuration.get_choices(self.organization)
        self.fields["address"].choices = Address.get_choices(self.organization)
        self.fields["media"].choices = Media.get_choices()

    config = forms.ChoiceField(choices=[])
    media = forms.ChoiceField(choices=[])
    quantity = forms.IntegerField(min_value=1, max_value=10, initial=1)
    address = forms.ChoiceField(choices=[])

    def clean_config(self):
        config = Configuration.get_or_none(self.cleaned_data.get("config"))
        if config is None or config.organization != self.organization:
            raise forms.ValidationError("Not your configuration", code="invalid")
        return config

    def clean_address(self):
        address = Address.get_or_none(self.cleaned_data.get("address"))
        if address is None or address.organization != self.organization:
            raise forms.ValidationError("Not your address", code="invalid")
        return address

    def clean_media(self):
        media = Media.get_or_none(self.cleaned_data.get("media"))
        if media is None:
            raise forms.ValidationError("Incorrect Media", code="invalid")
        return media

    def clean(self):
        cleaned_data = super().clean()
        config = cleaned_data.get("config")
        media = cleaned_data.get("media")

        if config is not None and media is not None and not config.can_fit_on(media):
            min_media = Media.get_min_for(config.size)
            if min_media is None:
                msg = "There is no large enough Media for this config."
                field = "config"
            else:
                msg = "Media not large enough for config (use at least {})".format(min_media.name)
                field = "media"
            self.add_error(field, msg)

    def save(self, *args, **kwargs):
        return "**FAKE**"

    @classmethod
    def success_message(cls, res):
        return "Successfuly created Order <em>{}</em>".format(res)


@login_required
def home(request):
    context = {"support_email": settings.SUPPORT_EMAIL}

    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as exp:
                logger.error(exp)
                messages.error(
                    request,
                    "Failed to update your password although it looks good. (ref: {exp})".format(
                        exp=exp
                    ),
                )
            else:
                messages.success(request, "Password Updated successfuly !")
                update_session_auth_hash(request, form.user)
                return redirect("home")
    else:
        form = PasswordChangeForm(user=request.user)
    context["password_form"] = form
    return render(request, "home.html", context)


@login_required
def orders(request):
    context = {
        "addresses": Address.objects.filter(
            organization=request.user.profile.organization
        )
    }

    forms_map = {"address_form": AddressForm, "order_form": OrderForm}

    # assume GET
    for key, value in forms_map.items():
        context[key] = value(prefix=key, organization=request.user.profile.organization)

    if request.method == "POST" and request.POST.get("form") in forms_map.keys():

        # which form is being saved?
        form_key = request.POST.get("form")
        context[form_key] = forms_map.get(form_key)(
            request.POST,
            prefix=form_key,
            organization=request.user.profile.organization,
        )

        if context[form_key].is_valid():
            try:
                res = context[form_key].save()
            except Exception as exp:
                logger.error(exp)
                messages.error(request, "Error while saving… {exp}".format(exp=exp))
            else:
                messages.success(request, context[form_key].success_message(res))
                return redirect("orders")
    else:
        pass

    return render(request, "orders.html", context)


@login_required
def delete_address(request, address_id=None):

    address = Address.get_or_none(address_id)
    if address is None:
        raise Http404("Configuration not found")

    if address.organization != request.user.profile.organization:
        raise HttpResponse("Unauthorized", status=401)

    try:
        address.delete()
        messages.success(request, "Successfuly deleted Address <em>{}</em>".format(address))
    except Exception as exp:
        logger.error("Unable to delete Address {id}: {exp}".format(id=address.id, exp=exp))
        messages.error(request, "Unable to delete Address <em>{addr}</em>: -- ref {exp}".format(addr=address, exp=exp))

    return redirect("orders")
