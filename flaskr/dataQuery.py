import functools
import xlrd
import csv
import os
import jellyfish
import pandas as pd
import json
from flask import (
    Blueprint, flash, g, redirect, request, session, url_for
)

bp = Blueprint('dataQuery', __name__, url_prefix='/privatelending')

class PrivateLendingRules():
    table_header = ["类别", "争议焦点（标题）", "裁判观点", "裁判依据", "说理", "判例"]
    data_filepath = "./data/"
    src_excel_filename = "裁判规则库 1220.xlsx"
    dst_csv_filename = "裁判规则库 1220.csv"
    csv_data = ""

    def __init__(self):
        if not os.path.exists(self.data_filepath):
            os.makedirs(self.data_filepath)
        if not os.path.exists(self.data_filepath + self.dst_csv_filename):                    # 没有CSV文件
            if os.path.exists(self.src_excel_filename):
                self.wash_data(self.src_excel_filename)
            elif os.path.exists(self.data_filepath + self.src_excel_filename):
                self.wash_data(self.data_filepath + self.src_excel_filename)
            else:
                print("error: 找不到文件" + self.src_excel_filename)
        self.csv_data = pd.read_csv(self.data_filepath + self.dst_csv_filename, encoding="utf-8-sig", index_col=False,
                                    keep_default_na=False)

    def split_excel_data(self):                                         # 将总表按类别分类，单独以CSV格式存储
        # with xlrd.open_workbook(excel_filename) as workbook:
        #     # name_sheets = workbook.sheet_names()                      # 获取Excel的sheet表列表，存储是sheet表名
        #     sheet = workbook.sheet_by_name('Sheet1')
        #     row_num = sheet.nrows
        #     col_mum = sheet.ncols
        #     merge_cells = sheet.merged_cells                            # 返回合并单元格列表 （起始行，结束行，起始列，结束列）  不包含
        #
        #     title_rows_index_list = []
        #     for merge_cell in merge_cells:
        #         title_rows_index_list.append(merge_cell[0])             # 规则库.xlsx 都是单行合并，合并单元格行号即标题所在行
        #         table_filepath = self.data_filepath + sheet.cell_value(merge_cell[0], 0) + ".csv"
        #         # print(table_title)
        #
        #         if not os.path.exists(table_filepath):                          # 为每个title创建一个csv文件
        #             with open(table_filepath, mode="w", encoding="utf-8-sig") as csv_f:
        #                 csv_writer = csv.writer(csv_f)
        #                 csv_writer.writerow(self.table_header)
        #
        #     title_rows_index_list.sort()                                # 行号从小到大排序
        #     # print(title_rows_index_list)
        #
        #     for row_index in range(1, row_num):                         # 跳过表头
        #         if row_index in title_rows_index_list:
        #             table_title = sheet.cell_value(row_index, 0)
        #             table_filepath = self.data_filepath + table_title + ".csv"
        #             print(table_filepath)
        #             continue
        #         else:
        #             with open(table_filepath, mode='a', newline='', encoding='utf-8-sig') as csv_f:
        #                 csv_writer = csv.writer(csv_f)
        #                 row_data = []
        #                 for col_index in range(col_mum):
        #                     row_data.append(str(sheet.cell_value(row_index, col_index)))
        #                 csv_writer.writerow(row_data)
        pass

    def wash_data(self, excel_filepath):                                             # 将excel总表转为csv格式
        dst_csv_filepath = self.data_filepath + self.dst_csv_filename
        with open(dst_csv_filepath, mode="w", encoding="utf-8-sig") as csv_f:
            csv_writer = csv.writer(csv_f)
            csv_writer.writerow(self.table_header)

        with xlrd.open_workbook(excel_filepath) as workbook:
            # name_sheets = workbook.sheet_names()                      # 获取Excel的sheet表列表，存储是sheet表名
            sheet = workbook.sheet_by_name('Sheet1')
            row_num = sheet.nrows
            col_mum = sheet.ncols
            merge_cells = sheet.merged_cells                            # 返回合并单元格列表 （起始行，结束行，起始列，结束列）  不包含

            title_rows_index_list = []
            for merge_cell in merge_cells:
                title_rows_index_list.append(merge_cell[0])             # 规则库.xlsx 都是单行合并，合并单元格行号即标题所在行
            title_rows_index_list.sort()                                # 行号从小到大排序

            for row_index in range(1, row_num):                         # 跳过表头s
                if row_index in title_rows_index_list:
                    table_title = sheet.cell_value(row_index, 0).split("、")[1]      # 去除标号
                    print(table_title)
                    continue
                else:
                    with open(dst_csv_filepath, mode='a', newline='', encoding='utf-8-sig') as csv_f:
                        csv_writer = csv.writer(csv_f)
                        row_data = [table_title]
                        for col_index in range(col_mum):
                            row_data.append(str(sheet.cell_value(row_index, col_index)))
                        csv_writer.writerow(row_data)

    def store_data(self):
        for fpath, dirname, fnames in os.walk(self.data_filepath):
            print(fnames)  # 所有的文件夹路径

    # def find(self):
    #     from fuzzywuzzy import fuzz
    #     from fuzzywuzzy import process
    #     choices = ["当事人双方均为台湾居民，借贷关系发生在台湾，但被告在大陆有固定住所，也有可供执行的财产，大陆法院对此类纠纷有管辖权。", "当事人对具有强制执行效力的公证借条的内容有争议提起的诉讼，仅在不予受理申请执行、驳回执行或不予出具执行证书等情况下方可向人民法院提起诉讼。"]
    #     print(process.extract("财产", choices, limit=10))
    #     print(process.extractOne("公证借条", choices))
    #     pass

    def get_closest_match(self, search_field_type, search_str):
        """
        输入：  search_field_type       检索字段类型，
               search_str              检索内容，返回前10最近似匹配结果，json格式。

        输出：  以json格式，返回前10最近似匹配结果。
        """
        closest_match_num = 10
        match_rusult_dict = {}
        field_types = ["争议焦点", "裁判观点", "裁判依据", "说理", "判例"]

        if search_field_type not in field_types:
            print("error:检索字段选择错误！")
            return -1
        select_csv_data = self.csv_data[["类别", search_field_type]]

        for index, row in select_csv_data.iterrows():
            match_score = jellyfish.jaro_winkler_similarity(search_str, row[search_field_type])
            match_rusult_dict[index] = match_score
            # print(index, " ", row, " ",match_score)
        match_result_sorted_dict = sorted(match_rusult_dict.items(), key=lambda v: v[1], reverse=True)
        match_result_top_dict = match_result_sorted_dict[:closest_match_num]

        items_info = dict()
        for index in range(len(match_result_top_dict)):
            match_result = match_result_top_dict[index]
            item_info = dict()
            item_info['类别'] = self.csv_data.loc[match_result[0], "类别"]
            item_info['争议焦点'] = self.csv_data.loc[match_result[0], "争议焦点（标题）"]
            item_info['裁判观点'] = self.csv_data.loc[match_result[0], "裁判观点"]
            item_info['裁判依据'] = self.csv_data.loc[match_result[0], "裁判依据"]
            item_info['说理'] = self.csv_data.loc[match_result[0], "说理"]
            item_info['判例'] = self.csv_data.loc[match_result[0], "判例"]
            items_info["item" + str(index + 1)] = item_info
        items_info = json.dumps(items_info, ensure_ascii=False)
        return items_info

@bp.route('/dataQuery',methods=(['POST','GET']))
def query_data():
    if request.method == 'POST':
        print(request.form)
        search_field_type = request.form['search_field_type']
        search_str = request.form['search_str']
        # print('1233344444'+search_field_type, search_str)
        myrules = PrivateLendingRules()
        res = myrules.get_closest_match(search_field_type, search_str)
    else:
        res = '无法使用GET方法访问'
    return res

