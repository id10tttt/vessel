# -*- coding: utf-8 -*-
import subprocess
from tempfile import NamedTemporaryFile
import os

BASE_PATH = '/tmp'


def convert_excel_to_pdf(excel_path, excel_name):
    execute_cmd = 'localc --headless --convert-to pdf --outdir {} {}'.format(BASE_PATH, excel_path)
    subprocess.run(execute_cmd, shell=True, executable="/bin/bash")
    pdf_path = BASE_PATH + '/{}.pdf'.format(excel_name)
    return pdf_path


if __name__ == '__main__':
    pdf_path = convert_excel_to_pdf('/home/jx/Pictures/c/SCSP23110144.xlsx', 'SCSP23110144')
    print('pdf_path: ', pdf_path)