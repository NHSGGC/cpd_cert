from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

from settings import (
    INPUT_PDF_PATH,
    OUTPUT_PDF_PATH,
    NAME_OFFSET_INCHES,
    GDC_OFFSET_INCHES,
)


def modify_pdf(name, gdc_number, input_path=INPUT_PDF_PATH, output_path=OUTPUT_PDF_PATH,
               name_offset_inch=NAME_OFFSET_INCHES,
               gdc_offset_inch=GDC_OFFSET_INCHES):
    packet = io.BytesIO()
    # create a new PDF with Reportlab
    can = canvas.Canvas(packet, pagesize=letter, bottomup=0)
    can.drawString(name_offset_inch['x'] * inch, name_offset_inch['y'] * inch, name)
    can.drawString(gdc_offset_inch['x'] * inch, gdc_offset_inch['y'] * inch, gdc_number)
    can.save()

    # move to the beginning of the StringIO buffer
    packet.seek(0)
    new_pdf = PdfFileReader(packet)
    # read your existing PDF
    existing_pdf = PdfFileReader(open(input_path, "rb"))
    output = PdfFileWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page = existing_pdf.getPage(0)
    page.mergePage(new_pdf.getPage(0))
    output.addPage(page)
    # finally, write "output" to a real file
    output_stream = open(output_path, "wb")
    output.write(output_stream)
    output_stream.close()


if __name__ == "__main__":
    modify_pdf("Joe Bloggs", 12345678)
