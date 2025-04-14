from io import StringIO
import csv
from fpdf import FPDF
from django.http import HttpResponse


def export_shopping_cart_txt(ingredients):
    content = "\n".join(
        f"{i['name']} ({i['measurement_unit']}) — {i['amount']}"
        for i in ingredients
    )
    response = HttpResponse(content, content_type="text/plain")
    response['Content-Disposition'] = ('attachment; '
                                       'filename="shopping_cart.txt"')
    return response


def export_shopping_cart_csv(ingredients):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])
    for i in ingredients:
        writer.writerow([i['name'], i['amount'], i['measurement_unit']])
    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response['Content-Disposition'] = ('attachment; '
                                       'filename="shopping_cart.csv"')
    return response


def export_shopping_cart_pdf(ingredients):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Список покупок", ln=True, align='C')

    for i in ingredients:
        pdf.cell(
            200,
            10,
            txt=f"{i['name']} ({i['measurement_unit']}) — {i['amount']}",
            ln=True
        )

    response = HttpResponse(pdf.output(dest='S').encode('latin1'),
                            content_type='application/pdf')
    response['Content-Disposition'] = ('attachment; '
                                       'filename="shopping_cart.pdf"')
    return response
