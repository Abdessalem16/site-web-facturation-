
from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from django.contrib import messages
from django.template.loader import get_template
from django.db import transaction
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

import pdfkit
import datetime

from .models import *
from .decorators import *
from .utils import pagination, get_invoice

class HomeView(LoginRequiredSuperuserMixim, View):
    """Main view"""

    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        invoices = Invoice.objects.select_related(
            'customer', 'save_by'
        ).all().order_by('-invoice_date_time')

        items = pagination(request, invoices)

        context = {
            'invoices': items
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        if request.POST.get('id_modified'):
            paid = request.POST.get('modified')

            try:
                obj = Invoice.objects.get(
                    id=request.POST.get('id_modified')
                )

                obj.paid = paid == 'True'
                obj.save()

                messages.success(
                    request,
                    _("Change made successfully.")
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Sorry, the following error has occurred: {e}"
                )

        if request.POST.get('id_supprimer'):

            try:
                obj = Invoice.objects.get(
                    pk=request.POST.get('id_supprimer')
                )

                obj.delete()

                messages.success(
                    request,
                    _("The deletion was successful.")
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Sorry, the following error has occurred: {e}"
                )

        invoices = Invoice.objects.select_related(
            'customer', 'save_by'
        ).all().order_by('-invoice_date_time')

        items = pagination(request, invoices)

        context = {
            'invoices': items
        }

        return render(request, self.template_name, context)


class AddCustomerView(LoginRequiredSuperuserMixim, View):
    """Add new customer"""

    template_name = 'add_customer.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):

        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
            'sex': request.POST.get('sex'),
            'age': request.POST.get('age'),
            'city': request.POST.get('city'),
            'zip_code': request.POST.get('zip'),
            'save_by': request.user,
        }

        try:
            Customer.objects.create(**data)

            messages.success(
                request,
                "Customer registered successfully."
            )

            return redirect('add-customer')

        except Exception as e:
            messages.error(
                request,
                f"Sorry, our system detected the following issue: {e}"
            )

            return render(request, self.template_name)


class AddInvoiceView(LoginRequiredSuperuserMixim, View):
    """Add a new invoice"""

    template_name = 'add_invoice.html'

    def get(self, request, *args, **kwargs):
        customers = Customer.objects.select_related(
            'save_by'
        ).all()

        context = {
            'customers': customers
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        items = []

        try:
            customer = request.POST.get('customer')
            invoice_type = request.POST.get('invoice_type')

            articles = request.POST.getlist('article')
            qties = request.POST.getlist('qty')
            units = request.POST.getlist('unit')
            total_a = request.POST.getlist('total-a')

            total = request.POST.get('total')
            comment = request.POST.get('comment')

            invoice_object = {
                'customer_id': customer,
                'save_by': request.user,
                'total': total,
                'invoice_type': invoice_type,
                'comments': comment,
            }

            invoice = Invoice.objects.create(
                **invoice_object
            )

            for index, article in enumerate(articles):

                data = Article(
                    invoice_id=invoice.id,
                    name=article,
                    quantity=qties[index],
                    unit_price=units[index],
                    total=total_a[index],
                )

                items.append(data)

            created = Article.objects.bulk_create(items)

            if created:
                messages.success(
                    request,
                    "Data saved successfully."
                )
            else:
                messages.error(
                    request,
                    "Sorry, please try again."
                )

        except Exception as e:
            messages.error(
                request,
                f"Sorry, the following error has occurred: {e}"
            )

        customers = Customer.objects.select_related(
            'save_by'
        ).all()

        context = {
            'customers': customers
        }

        return render(
            request,
            self.template_name,
            context
        )


class InvoiceVisualizationView(
    LoginRequiredSuperuserMixim, View
):
    """Visualize an invoice"""

    template_name = 'invoice.html'

    def get(self, request, *args, **kwargs):

        pk = kwargs.get('pk')

        context = get_invoice(pk)

        return render(
            request,
            self.template_name,
            context
        )


@superuser_required
def get_invoice_pdf(request, *args, **kwargs):
    """Generate PDF from HTML"""

    pk = kwargs.get('pk')

    context = get_invoice(pk)

    context['date'] = datetime.datetime.today()

    template = get_template('invoice-pdf.html')

    html = template.render(context)

    options = {
        'page-size': 'Letter',
        'encoding': 'UTF-8',
        'enable-local-file-access': ''
    }

    pdf = pdfkit.from_string(
        html,
        False,
        options
    )

    response = HttpResponse(
        pdf,
        content_type='application/pdf'
    )

    response['Content-Disposition'] = 'attachment'

    return response