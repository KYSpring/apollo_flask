import json
import datetime
from urllib import request as lprrequest

from flask import (
    Blueprint, flash, g, redirect, request, session, url_for
)

bp = Blueprint('calculateRate', __name__, url_prefix='/privatelending')

def round2(num):
    # 取3位小数
    return round(num, 2)

def round4(num):
    return round(num,4)

def get_lpr(inputdate):
    '''
    author by 刘天一liutianyi
    :param inputdate:exg. '2019-01-01'
    :return:
    '''
    from urllib import request as lprrequest
    enddate = inputdate
    if inputdate[5:7] == '01':
        startdate = str(int(inputdate[:4])-1)+'-12-01'
    else:
        startdate = inputdate[:5]+str(int(inputdate[5:7])-1)+'-01'
    url = 'http://www.chinamoney.com.cn/dqs/rest/cm-u-bk-currency/LprHis?lang=CN&strStartDate='+startdate+'&strEndDate='+enddate
    header = {'User-Agent': 'Mozilla/5.0 (Macntosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15'}
    req = lprrequest.Request(url, headers = header)
    content = lprrequest.urlopen(req).read().decode()
    jsc = json.loads(content)
    rec = jsc['records']
    if int(inputdate[:4])>2019 or (int(inputdate[:4])>=2019 and int(inputdate[5:7])>=8 and int(inputdate[8:10])>=20):
        return rec[0]['1Y'],rec[0]['5Y']
    else:
        return rec[0]['1Y']

@bp.route('/querylpr',methods=(['GET']))
def querylpr():
    if request.method == 'GET':
        querydate = request.args.get('date')
        querytype = request.args.get('type')
        oneyearrate,fiveyearrate = get_lpr(querydate)
        # print('oneyearrate,fiveyearrate',oneyearrate,fiveyearrate)
        if(querytype == '1' or querytype == 1):
            return oneyearrate
        else:
            return fiveyearrate

@bp.route('/calculateRate',methods=(['POST']))
def calculate_rate():
    if request.method == 'POST':
        data = json.loads(request.get_data())

        # 一些如果不填的默认值
        # 1.起算时间不填则默认为出借时间
        if len(data['LXAction']['LXLoan']['rateStartTime']) == 0:
            data['LXAction']['LXLoan']['rateStartTime'] = data['LXAction']['LXLoan']['loanLendTime']

        # 借款本金
        loanAmount = float(data['LXAction']['LXLoan']['loanAmount'])

        # 期内利率
        rate = float(data['LXAction']['LXLoan']['rate'])
        if data['LXAction']['LXLoan']['rateRadio']==0 or data['LXAction']['LXLoan']['rateRadio']=='0':
            rate = 0.0
        else:
            # 固定利率
            if data['LXAction']['LXLoan']['rateSelectValue'] == 1 or data['LXAction']['LXLoan']['rateSelectValue'] == '1':
                rate = float(data['LXAction']['LXLoan']['rate'])/100
            # 一年期LPR
            elif data['LXAction']['LXLoan']['rateSelectValue'] == 2 or data['LXAction']['LXLoan']['rateSelectValue'] == '2':
                rate,_ = get_lpr(str(data['LXAction']['LXLoan']['LPRdate']))
                rate =float(rate)/100
                rate = float(rate)*float(data['LXAction']['LXLoan']['LPRTimes'])
            # 五年期LPR，可能无数据
            elif data['LXAction']['LXLoan']['rateSelectValue'] == 3 or data['LXAction']['LXLoan']['rateSelectValue'] == '3':
                _,rate = get_lpr(str(data['LXAction']['LXLoan']['LPRdate']))
                rate =float(rate)/100
                rate = float(rate)*float(data['LXAction']['LXLoan']['LPRTimes'])

        #逾期利率
        overdueRate = float(data['LXAction']['LXLoan']['rate'])
        if data['LXAction']['LXLoan']['overdueRateRadio']==0 or data['LXAction']['LXLoan']['overdueRateRadio']=='0':
            overdueRate = 0.0
        else:
            # 固定利率
            if data['LXAction']['LXLoan']['overdueRateSelectValue'] == 1 or data['LXAction']['LXLoan']['overdueRateSelectValue'] == '1':
                overdueRate = float(data['LXAction']['LXLoan']['overdueRate'])/100
            # 一年期LPR
            elif data['LXAction']['LXLoan']['overdueRateSelectValue'] == 2 or data['LXAction']['LXLoan']['overdueRateSelectValue'] == '2':
                overdueRate,_ = get_lpr(str(data['LXAction']['LXLoan']['overdueLPRdate'])) #后续需要替换成选择日期
                overdueRate = float(overdueRate)/100
                overdueRate = float(overdueRate)*float(data['LXAction']['LXLoan']['overdueTimes'])
            # 五年期LPR，可能无数据
            elif data['LXAction']['LXLoan']['overdueRateSelectValue'] == 3 or data['LXAction']['LXLoan']['overdueRateSelectValue'] == '3':
                _,overdueRate = get_lpr(str(data['LXAction']['LXLoan']['overdueLPRdate'])) #后续需要替换成选择日期
                overdueRate = float(overdueRate)/100
                overdueRate = float(overdueRate)*float(data['LXAction']['LXLoan']['overdueTimes'])

        #还款记录数组
        LXRepayment = data['LXAction']['LXLoan']['LXRepayment']

        # 初始化待还利息、还本金总额和还利息总额
        waitRateAmount = 0.0
        totalPayPrin = 0.0
        totalPayRate = 0.0

        # 初始化计算过程记录
        activities = [
            {
                'content': "借款%.2f元;年利率%.4f。" % (loanAmount,rate),
                'timestamp': data['LXAction']['LXLoan']['loanLendTime'],
                'type': 'primary',
                'hollow': True,

            },
        ]

        # 处理每次还款
        for i in range(len(LXRepayment)):
            if LXRepayment[i]['repayPrincipal'] == 0 and LXRepayment[i]['repayRate'] == 0 and LXRepayment[i]['repayTotal'] == 0:
                continue
            #当期期内利率计算时间
            if data['LXAction']['LXLoan']['rateRadio'] == 0 or \
                    data['LXAction']['LXLoan']['rateRadio'] == '0' or \
                    len(LXRepayment[i]['rateTimeRange']) == 0:
                rateTimeRange = 0.0
            else:
                rateStartYear,rateStartMon,rateStartDay = \
                    int(LXRepayment[i]['rateTimeRange'][0].split('-')[0]),\
                    int(LXRepayment[i]['rateTimeRange'][0].split('-')[1]),\
                    int(LXRepayment[i]['rateTimeRange'][0].split('-')[2])
                rateTimeStart = datetime.datetime(rateStartYear,rateStartMon,rateStartDay)
                rateEndYear, rateEndMon, rateEndDay = \
                    int(LXRepayment[i]['rateTimeRange'][1].split('-')[0]), \
                    int(LXRepayment[i]['rateTimeRange'][1].split('-')[1]), \
                    int(LXRepayment[i]['rateTimeRange'][1].split('-')[2])
                rateTimeEnd = datetime.datetime(rateEndYear, rateEndMon, rateEndDay)
                rateTimeRange = float((rateTimeEnd - rateTimeStart).days)

            mathRecord = "(%.2f*%.d*%.4f/360)+%.2f(剩余利息)" % (loanAmount,rateTimeRange,rate,waitRateAmount)
            #当期待还期内利率为（本金*时间*年利率/360）+ 上次还款剩余利息
            waitRateAmount = float(loanAmount*rateTimeRange*rate/360) + waitRateAmount
            activities.append({
                'content': "当期利息:%.2f=%s。" % (waitRateAmount,mathRecord),
                'timestamp': LXRepayment[i]['repayTime'],
                'type': 'primary',
                'hollow': True,
            })

            #当期逾期利率计算时间
            if data['LXAction']['LXLoan']['overdueRateRadio'] == 0 or \
                    data['LXAction']['LXLoan']['overdueRateRadio'] == '0' or \
                    len(LXRepayment[i]['overdueTimeRange']) == 0:
                overdueRateTimeRange = 0.0
            else:
                overdueRateStartYear,overdueRateStartMon,overdueRateStartDay = \
                    int(LXRepayment[i]['overdueTimeRange'][0].split('-')[0]),\
                    int(LXRepayment[i]['overdueTimeRange'][0].split('-')[1]),\
                    int(LXRepayment[i]['overdueTimeRange'][0].split('-')[2])
                overdueRateTimeStart = datetime.datetime(overdueRateStartYear,overdueRateStartMon,overdueRateStartDay)
                overdueRateEndYear, overdueRateEndMon, overdueRateEndDay = \
                    int(LXRepayment[i]['overdueTimeRange'][1].split('-')[0]), \
                    int(LXRepayment[i]['overdueTimeRange'][1].split('-')[1]), \
                    int(LXRepayment[i]['overdueTimeRange'][1].split('-')[2])
                overdueRateTimeEnd = datetime.datetime(overdueRateEndYear, overdueRateEndMon, overdueRateEndDay)
                overdueRateTimeRange = float((overdueRateTimeEnd - overdueRateTimeStart).days)

            mathRecord ="%.2f*%d*%.4f/360" % (loanAmount,overdueRateTimeRange,overdueRate)
            # 当期待还逾期利率为（本金*时间*逾期年利率/360）
            waitOverdueRateAmount = float(loanAmount * overdueRateTimeRange * overdueRate / 360)
            activities.append({
                'content': "逾期利息:%.2f=%s。" % (waitOverdueRateAmount,mathRecord),
                'timestamp': LXRepayment[i]['repayTime'],
                'type': 'primary',
                'hollow': True,
            })

            # 当期偿还本金金额 和 偿还利息金额
            # 未约定则默认 先息后本
            curRepayPrin = 0.0
            curRepayRate = 0.0
            if LXRepayment[i]['repayPrincipalRadio'] == 0 or LXRepayment[i]['repayPrincipalRadio'] == '0':
                repayTotal = float(LXRepayment[i]['repayTotal'])
                if repayTotal >= waitRateAmount + waitOverdueRateAmount:
                    curRepayRate = waitRateAmount + waitOverdueRateAmount
                    curRepayPrin = repayTotal - curRepayRate
                else:
                    curRepayRate = repayTotal
                    curRepayPrin = 0.0
            # 否则根据实际填写的情况确认还款情况
            # 待考虑边界-如果还钱多于所亏欠的利息或本金怎么处理？？初步设想允许为负数
            else:
                curRepayRate = float(LXRepayment[i]['repayRate'])
                curRepayPrin = float(LXRepayment[i]['repayPrincipal'])

            totalPayPrin += curRepayPrin
            totalPayRate += curRepayRate

            # 剩余待还本金 和 剩余待还利息
            mathRecord1 = "%.2f-%.2f" % (loanAmount, curRepayPrin)
            mathRecord2 = " %.2f+%.2f-%.2f" % (waitRateAmount,waitOverdueRateAmount,curRepayRate)
            loanAmount -= curRepayPrin
            waitRateAmount = waitRateAmount + waitOverdueRateAmount - curRepayRate
            activities.append({
                'content': "剩余本金: %.2f=%s; 剩余利息: %.2f=%s" % (loanAmount,mathRecord1,waitRateAmount,mathRecord2),
                'timestamp': LXRepayment[i]['repayTime'],
                'type': 'primary',
                'hollow': True,
            })

        ## 计算到最终结算时的待还利息
        if len(data['LXAction']['LXLoan']['rateStartTime']) and \
                len(data['LXAction']['LXLoan']['loanEndTime']) and \
                len(data['LXAction']['LXLoan']['balanceTime']):
            # 最后一次还款时间，若无还款则初始值为利息起算时间
            lastRepayYear,lastRepayMon,lastRepayDay = \
                int(data['LXAction']['LXLoan']['rateStartTime'].split('-')[0]),\
                int(data['LXAction']['LXLoan']['rateStartTime'].split('-')[1]),\
                int(data['LXAction']['LXLoan']['rateStartTime'].split('-')[2]);
            lastRepayTime = datetime.datetime(lastRepayYear,lastRepayMon,lastRepayDay)
            repaymentNum = len(LXRepayment)
            # 更鲁棒的判断逻辑
            if repaymentNum >=1 and (LXRepayment[repaymentNum-1]['repayTime'] or LXRepayment[repaymentNum-1]['repayTotal']):
                lastRepayYear, lastRepayMon, lastRepayDay = \
                    int(LXRepayment[repaymentNum-1]['repayTime'].split('-')[0]), \
                    int(LXRepayment[repaymentNum-1]['repayTime'].split('-')[1]), \
                    int(LXRepayment[repaymentNum-1]['repayTime'].split('-')[2])
                lastRepayTime = datetime.datetime(lastRepayYear, lastRepayMon, lastRepayDay)

            # 获取本次借款到期时间（最终借款的逾期利息起算时间）
            loanEndYear, loanEndMon, loanEndDay = \
                int(data['LXAction']['LXLoan']['loanEndTime'].split('-')[0]), \
                int(data['LXAction']['LXLoan']['loanEndTime'].split('-')[1]), \
                int(data['LXAction']['LXLoan']['loanEndTime'].split('-')[2]);
            loanEndTime = datetime.datetime(loanEndYear, loanEndMon, loanEndDay)

            # 获取本次借款的结算时间
            balanceTimeYear, balanceTimeMon, balanceTimeDay = \
                int(data['LXAction']['LXLoan']['balanceTime'].split('-')[0]), \
                int(data['LXAction']['LXLoan']['balanceTime'].split('-')[1]), \
                int(data['LXAction']['LXLoan']['balanceTime'].split('-')[2]);
            balanceTime = datetime.datetime(balanceTimeYear, balanceTimeMon, balanceTimeDay)

            # 判断有无逾期利率，若有按逾期利率算，若无则按期内利率算
            if data['LXAction']['LXLoan']['overdueRateRadio'] == 1 or data['LXAction']['LXLoan']['overdueRateRadio'] == '1':
                finalOverdueTime = float((balanceTime - loanEndTime).days)
                if finalOverdueTime > 0:
                    # 至结算日新增期内利息
                    finalRateTime = max(float((loanEndTime - lastRepayTime).days), 0)
                    mathRecord = "(%.2f*%.d*%.4f/360)+%.2f(剩余利息)" % (loanAmount, finalRateTime, rate, waitRateAmount)
                    newRateAmount = loanAmount * finalRateTime * rate / 360
                    activities.append({
                        'content': "至结算日新增期内利息:%.2f=%s。" % (newRateAmount, mathRecord),
                        'timestamp': data['LXAction']['LXLoan']['balanceTime'],
                        'type': 'primary',
                        'hollow': True,
                    })

                    # 至结算日新增逾期利息
                    mathRecord = "(%.2f*%.d*%.4f/360)+%.2f(剩余利息)" % (loanAmount,finalOverdueTime,overdueRate,waitRateAmount)
                    newOverduRateAmount = loanAmount*finalOverdueTime*overdueRate/360
                    activities.append({
                        'content': "至结算日新增逾期利息:%.2f=%s。" % (newOverduRateAmount, mathRecord),
                        'timestamp': data['LXAction']['LXLoan']['balanceTime'],
                        'type': 'primary',
                        'hollow': True,
                    })

                    # 至结算日待还利息和
                    mathRecord = "(%.2f + %.2f + %.2f(剩余利息)" % (newRateAmount,newOverduRateAmount,waitRateAmount)
                    waitRateAmount = newRateAmount +newOverduRateAmount +waitRateAmount
                    activities.append({
                        'content': "待还利息和:%.2f=%s。" % (waitRateAmount, mathRecord),
                        'timestamp': data['LXAction']['LXLoan']['balanceTime'],
                        'type': 'primary',
                        'hollow': True,
                    })
            else:
                # 至结算日剩余利息加总
                finalTimeRange = float((balanceTime - lastRepayTime).days)
                mathRecord = "(%.2f*%.d*%.4f/360)+%.2f(剩余利息)" % (loanAmount,finalTimeRange,overdueRate,waitRateAmount)
                waitRateAmount += loanAmount*finalTimeRange*rate/360
                activities.append({
                    'content': "至结算日待还利息和:%.2f=%s。" % (waitRateAmount, mathRecord),
                    'timestamp': data['LXAction']['LXLoan']['balanceTime'],
                    'type': 'primary',
                    'hollow': True,
                })

        #计算结果
        waitPayData = [
            {
                'value': round2(loanAmount),
                'name': '待还本金（元）',
            },
            {
                'value': round2(waitRateAmount),
                'name': '待还利息（元）',
            },
        ]
        paidData = [
            {
                'value': round2(totalPayPrin),
                'name': '已还本金（元）',
            },
            {
                'value': round2(totalPayRate),
                'name': '已还利息（元）',
            },
        ]

        res = {
            "code": 200,
            "data": {
                'waitPayData':waitPayData,
                'paidData':paidData,
                'activities':activities
            },
        }
    else:
        res = '无法使用GET方法访问'
    return res

if  __name__ == '__main__':
    get_lpr('2020-01-01')
