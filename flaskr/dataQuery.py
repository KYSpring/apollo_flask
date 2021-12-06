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
    table_header = ["争议一级", "争议二级", "争议焦点", "裁判观点", "裁判依据", "说理", "判例"]
    data_filepath = './data/' # flask运行时候的根目录和单独运行本py文件的根目录是不一样的
    src_excel_filename = "裁判规则库20211026争议焦点体系终.xls"
    dst_csv_filename = "裁判规则库20211026争议焦点体系终.csv"

    csv_data = ""

    def __init__(self):
        if not os.path.exists(self.data_filepath):
            os.makedirs(self.data_filepath)
        if not os.path.exists(self.data_filepath + self.dst_csv_filename):                    # 没有CSV文件
            if os.path.exists(self.src_excel_filename):
                self.wash_data(self.src_excel_filename)
            elif os.path.exists(self.data_filepath + self.src_excel_filename):
                print('bad')
                self.wash_data(self.data_filepath + self.src_excel_filename)
            else:
                print("error: 找不到文件 " + self.src_excel_filename)
        self.csv_data = pd.read_csv(self.data_filepath + self.dst_csv_filename, encoding="utf-8-sig", index_col=False,
                                   keep_default_na=False)

    def wash_data(self, excel_filepath):                                             # 将excel总表转为csv格式
        dst_csv_filepath = self.data_filepath + self.dst_csv_filename
        with open(dst_csv_filepath, mode="w",newline='', encoding="utf-8-sig") as csv_f:
            csv_writer = csv.writer(csv_f)
            csv_writer.writerow(self.table_header)

        print(excel_filepath)
        with xlrd.open_workbook(excel_filepath, formatting_info=True) as workbook:
            # name_sheets = workbook.sheet_names()                      # 获取Excel的sheet表列表，存储是sheet表名
            sheet = workbook.sheet_by_name('Sheet1')
            row_num = sheet.nrows
            col_mum = sheet.ncols
            merge_cells = sheet.merged_cells                            # 返回合并单元格列表 （起始行，结束行，起始列，结束列）  不包含

            title_rows_index_list = [] # 一级标签记录行号即可
            second_label_index_list = [] #二级标签记录行号范围
            for merge_cell in merge_cells:
                if merge_cell[1]-merge_cell[0]==1 and merge_cell[3]-merge_cell[2]>3:
                    title_rows_index_list.append(merge_cell[0])             # 规则库.xls 都是单行合并，合并单元格行号即标题所在行
                elif merge_cell[2]==0:
                    second_label_index_list.append([merge_cell[0],merge_cell[1]])
            title_rows_index_list.sort()                                # 行号从小到大排序
            second_label_index_list.sort()
            print('一级',title_rows_index_list)
            print('二级',second_label_index_list)
            second_point = 0;
            for row_index in range(1, row_num):                         # 跳过表头s
                if row_index in title_rows_index_list:
                    table_title = sheet.cell_value(row_index, 0).split("、")[1]      # 去除标号
                    # print('table_title', table_title)
                    continue
                else:
                    if row_index >= second_label_index_list[second_point][1]:
                        second_point = second_point+1
                    second_label = sheet.cell_value(second_label_index_list[second_point][0],0);
                    # print(second_label,row_index, second_label_index_list[second_point][1])
                    with open(dst_csv_filepath, mode='a', newline='', encoding='utf-8-sig') as csv_f:
                        csv_writer = csv.writer(csv_f)
                        row_data = [table_title, second_label]
                        for col_index in range(1, col_mum):
                            row_data.append(str(sheet.cell_value(row_index, col_index)))
                        csv_writer.writerow(row_data)

    def store_data(self):
        for fpath, dirname, fnames in os.walk(self.data_filepath):
            print(fnames)  # 所有的文件夹路径

    def get_class_list(self):
        '获取争议一级标签'
        """
        输出：争议一级标签class_list（格式为list），争议二级（格式为list[list]）issue_list_sum ;（同一索引序号的两个list为对应关系:即 （索引序号=争议一级序号=争议二级集合序号））
        """
        class_list = list(set(self.csv_data["争议一级"].values.tolist()))
        class_list.sort()
        issue_list_sum = []
        for item in class_list:
            issue_list_sum.append(self.get_issue_list(item))
        return class_list, issue_list_sum

    def get_issue_list(self, class_type):
        """
             获取争议一级下的争议二级清单
             输入 一级类别class_type
             输出 该类别下的争议焦点清单：list
        """
        issue_list = list(set(self.csv_data[["争议一级", "争议二级"]][self.csv_data["争议一级"] == class_type]["争议二级"]))
        # print('issue-list',class_type,issue_list)
        return issue_list

    def get_closest_match(self, search_field_type, search_str, search_class):
        """
        输入：  search_field_type       检索字段类型，["争议二级","争议焦点", "裁判观点", "裁判依据", "说理", "判例"]，若用户未选中，则默认争议焦点；
               search_str              检索内容，返回前closest_match_num个最近似匹配结果，json格式。[检索框中填写的文本or争议焦点]
               search_class            争议一级
        (注意，由于筛选和检索共用一个接口，当做筛选接口使用的时候，只需要search_class作为争议一级，search_field_type="争议二级" search_str = 争议二级的文本内容 即可)
        输出：  以json格式，返回前10最近似匹配结果。
        """
        closest_match_num = 20
        match_rusult_dict = {}
        field_types = ["争议二级", "争议焦点", "裁判观点", "裁判依据", "说理", "判例"]
        if search_field_type not in field_types:
            print("error:检索字段选择错误！")
            return -1
        if search_class == '':
            select_csv_data = self.csv_data[["争议一级", search_field_type]]
        else:
            select_csv_data = self.csv_data[["争议一级", search_field_type]][self.csv_data["争议一级"] == search_class]
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
            item_info['争议一级'] = self.csv_data.loc[match_result[0], "争议一级"]
            item_info['争议二级'] = self.csv_data.loc[match_result[0], "争议二级"]
            item_info['争议焦点'] = self.csv_data.loc[match_result[0], "争议焦点"]
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
        # print(request.form)
        search_field_type = request.form['search_field_type']
        search_str = request.form['search_str']
        search_class = request.form['search_class']
        myrules = PrivateLendingRules()
        # print(search_field_type, search_str, search_class);
        res = myrules.get_closest_match(search_field_type, search_str, search_class)
    else:
        res = '无法使用GET方法访问'
    return res

@bp.route('/getClassList', methods=(['GET']))
def get_class():
    """
    :return:    返回一级分类list和对应的争议焦点List
    """
    if request.method == 'GET':
        myclass = PrivateLendingRules()
        res = {'state':True,'info': myclass.get_class_list()}
    else:
        res = {'state':True, 'info':'无法使用POST方法访问'}
    return res

if  __name__ == '__main__':
    wangshaochun = PrivateLendingRules()
    # wangshaochun.wash_data('C:\清华大学\计算法学项目\项目15\\20201212类案检索+裁判规则库\cpgzk-flask\\apollo_flask\data\裁判规则库 20210220 修改版.xlsx')
    print('good')