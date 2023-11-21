# -*- coding: utf-8 -*-
import subprocess

BASE_PATH = '/tmp'


# Libreoffice-calc
def convert_excel_to_pdf(excel_path, excel_name):
    execute_cmd = 'localc --headless --convert-to pdf --outdir {} {}'.format(BASE_PATH, excel_path)
    subprocess.run(execute_cmd, shell=True, executable="/bin/bash")
    pdf_path = BASE_PATH + '/{}.pdf'.format(excel_name)
    return pdf_path


if __name__ == '__main__':
    pass
