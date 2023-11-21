# -*- coding: utf-8 -*-
from tempfile import NamedTemporaryFile
from PIL import Image as pilImage
from PIL import ImageDraw
from PIL import ImageFont
import os
import logging

_logger = logging.getLogger(__name__)

try:
    import fitz

    fitz.Document()
except Exception as e:
    from fitz import fitz

BASE_TMP_PATH = '/tmp'


class ProcessPDF:
    def __init__(self, pdf_content, seal, pdf_file_path=None, water_mark_txt=None, font_path='Candaral.ttf',
                 clarity=1.34):
        self.pdf_content = pdf_content
        self.seal = seal
        self.pdf_file_path = pdf_file_path
        self.water_mark_txt = water_mark_txt
        self.font_path = font_path
        self.clarity = clarity

    def merge_img(self, pdf_png):
        """
        图片叠加
        """
        img1 = pilImage.open(pdf_png)  # PDF图片
        seal_img = pilImage.open(self.seal)  # 公司印章图片
        # 缩放seal
        # seal_img = seal_img.resize((int(seal_img.size[0] * 0.6), int(seal_img.size[0] * 0.6)), pilImage.ANTIALIAS)
        layer = pilImage.new('RGBA', (img1.size[0], img1.size[1] - 200), (0, 0, 0, 0))
        layer.paste(seal_img, (img1.size[0] - 380, img1.size[1] - 380))
        out = pilImage.composite(layer, img1, layer)
        if self.water_mark_txt:
            fonts = ImageFont.truetype(self.font_path, size=30)
            draw_obj = ImageDraw.Draw(out)
            draw_obj.text((img1.size[0] - 300, img1.size[1] - 250), self.water_mark_txt, fill=(0, 0, 0), font=fonts)
        with NamedTemporaryFile() as tmp_img:
            tmp_img_name = '{}/{}.png'.format(BASE_TMP_PATH, tmp_img)
            out.save(tmp_img_name)
            return tmp_img_name, tmp_img

    def pdf_to_img(self):
        """
        PDF转化为图片
        """
        if self.pdf_file_path:
            doc = fitz.Document(self.pdf_file_path)
        else:
            doc = fitz.Document(stream=self.pdf_content)
        # for pg in range(doc.page_count):
        page = doc[0]
        rotate = int(0)
        zoom_x = self.clarity
        zoom_y = self.clarity
        trans = fitz.Matrix(zoom_x, zoom_y).prerotate(rotate)
        pm = page.get_pixmap(matrix=trans, alpha=False)
        with NamedTemporaryFile() as pdf_png:
            pdf_png_name = '{}/{}.png'.format(BASE_TMP_PATH, pdf_png)
            pm._writeIMG(pdf_png_name, 1, jpg_quality=95)
        return pdf_png_name, pdf_png

    def img_to_pdf(self, img_file):
        """
        图片转化为PDF
        """
        doc = fitz.Document()
        imgdoc = fitz.Document(img_file)
        pdfbytes = imgdoc.convert_to_pdf()  # 使用图片创建单页的 PDF
        imgpdf = fitz.Document("pdf", pdfbytes)
        doc.insert_pdf(imgpdf)  # 将当前页插入文档
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def out(self):
        pdf_png_name, pdf_png = self.pdf_to_img()  # PDF转化为图片
        img_file_name, img_file = self.merge_img(pdf_png_name)  # 合并图片
        pdf_file = self.img_to_pdf(img_file_name)  # 图片转化为PDF
        try:
            os.unlink(pdf_png_name)
            os.unlink(img_file_name)
        except Exception as e:
            _logger.error('删除文件出错: {}'.format(e))
        return pdf_file


if __name__ == '__main__':
    """
    pdf_path: PDF文件的路径
    pdf_name：PDF文件名
    pdf_out_path：PDF输出路径
    pdf_out_name：PDF输出文件名
    seal: 公章路径
    clarity：可选参数，可以调整pdf清晰度，默认1.34，数值越大，清晰度越高
    """
    seal = 'seal.png'
    pdf_file_path = fitz.Document('doc1.pdf')
    pdf = ProcessPDF(pdf_file_path=pdf_file_path, pdf_content='', seal=seal, clarity=1)
    pdf_file = pdf.out()
