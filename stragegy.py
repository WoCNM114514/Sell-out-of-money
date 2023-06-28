# -*- coding: utf-8 -*-
'''
Spyder Editor

'''

#@ author: Jiaixng Wei 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(font="SimHei") # 中文
plt.rcParams['axes.unicode_minus']=False # 负号


'''
策略思路: 纯卖出深度虚值看涨期权, 利用此类期权gamma绝对值小的特点规避临近行权日的权利金大幅度
波动, 同时降低期权转为实值造成的损失
实现方式: 每周买入虚值程度最高的若干份合约, 锁仓一星期, 在下个星期卖开平仓 
'''

class OptionStrategy:
    def __init__(self, data, period, capital, amount):
        '''
        data: df文件, 原始的期权合约数据
        period: int, 表示调仓周期
        capital: int, 资金总量
        amount: int, 持仓数量
        '''
        self.data = data
        self.period = period
        self.capital = capital
        self.amount = amount
    
    def log(self, trade_date, selected_ids): # 记录交易记录
        period = self.period
        buy_date = (pd.to_datetime(trade_date) - pd.DateOffset(days=period)).strftime('%Y-%m-%d') # 买入日期
        for selected_id in selected_ids:
            print(f"交易记录:买平 - {buy_date}, 卖开 - {trade_date}, 合约代码 - {selected_id}")

    def selectTopN(self, tmp): # 筛选函数
        N = self.amount
        tmp = tmp.copy()
        symbols = tmp.nlargest(N).index
        tmp[:] = 0
        tmp[symbols] = 1
        return tmp
    
    def spread_matrix(self): # 价差矩阵
        period = self.period
        self.data['TradingDate'] = pd.to_datetime(self.data['TradingDate'])
        self.data['ExerciseDate'] = pd.to_datetime(self.data['ExerciseDate'])
        tmp = self.data[['Symbol', 'TradingDate', 'price_spread']].pivot(index='TradingDate', columns='Symbol', values='price_spread')
        tmp = tmp.iloc[::period]
        return tmp
    
    def return_matrix(self): # 收益矩阵
        '''
        收益计算方法: 收益率 * 总手数 * 合约乘数
        '''
        period = self.period
        capital = self.capital
        self.data['TradingDate'] = pd.to_datetime(self.data['TradingDate'])
        close = self.data[['Symbol', 'TradingDate', 'ClosePrice']].pivot(index='TradingDate', columns='Symbol', values='ClosePrice')
        close = close * 100 * capital / 100 # 300ETF的收益
        #close = close * 300 * capital / 100 # 50ETF的收益
        close = close.iloc[::period] 
        ret = close.pct_change().fillna(0) # 按输入调仓频率得到的收益矩阵
        return ret
    
    def backtest(self): # 回测部分
        N = self.amount
        capital = self.capital
        spread = self.spread_matrix()
        ret = -self.return_matrix() # 卖方收益
        signal = spread.apply(self.selectTopN, axis=1)
        
        # 打印交易记录
        for date, row in signal.iterrows():
            symbols = row[row==1].index.tolist()
            if len(symbols) > 0:
                trade_date = date.strftime('%Y-%m-%d')
                selected_ids = symbols
                self.log(trade_date, selected_ids)
                
        profit = (signal * ret * capital / 100).sum(axis=1) / (N * capital)
        pnl = (profit + 1).cumprod().fillna(method='pad') # 策略的净值
        pnl.plot(figsize=(12,6), grid=True, label=f'纯卖虚:合约数{N}张')
        plt.title('纯卖虚值策略_2023_06_27')
        plt.legend()
        plt.show()
        
        # 绩效分析
        maxdd = lambda profit: (1-(1+profit).cumprod()/(1+profit).cumprod().expanding().max()).max()
        sharpe=lambda profit:(profit.mean() / profit.std()) * (243**0.5)
        gain_total=lambda profit:(1+profit).prod()-1
        gain_yearly=lambda profit:(1+profit).prod()**(243/len(profit))-1
        calmar=lambda profit:gain_yearly(profit)/maxdd(profit)

        d={
            '总收益': '{:.3%}'.format(gain_total(profit)),
            '年化收益': '{:.3%}'.format(gain_yearly(profit)),
            '最大回撤': '{:.3%}'.format(maxdd(profit)),
            '夏普率':sharpe(profit),
            '卡玛率':calmar(profit),
            '策略资金容量': capital
            }
        print(d)


# ——————————————————————————Backtest Interface—————————————————————————————————
df = pd.read_excel(r'C:\Users\20536\Desktop\rock\策略研究\期权组合\300虚值期权.xlsx')
strategy = OptionStrategy(data=df, period=5, capital=1000000, amount=5)
strategy.backtest()