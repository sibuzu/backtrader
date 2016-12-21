#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015, 2016 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse

import jack.tradedata as td
import backtrader as bt
import backtrader.feeds as btfeeds
from backtrader.plot.scheme import PlotScheme
import pandas as pd


class MyStrategy(bt.Strategy):
    params = dict(
        printout=False
    )

    def log(self, txt, dt=None):
        if self.p.printout:
            dt = dt or self.data.datetime[0]
            dt = bt.num2date(dt)
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        self.order = 0  # sentinel to avoid operrations on pending order
        self.diff = self.getdatabyname('diff').close

    def next(self):
        dt = self.data.datetime.date()

        self.log('BAR {}, {}, {}, {}, {}, {}'.format(self.datas[0].open[0], 
            self.datas[0].high[0],
            self.datas[0].low[0],
            self.datas[0].close[0], 
            self.datas[1].close[0], 
            self.diff[0]))
        sz = self.position.size
        if self.diff[0] > 0:
            if sz >= 0:
                self.sell(size=sz+1, checksubmit=False)
        elif self.diff[0] < 0:
            if sz <= 0:
                self.buy(size=-sz+1, checksubmit=False, )

    def notify_order(self, order):
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            return  # Await further notifications

        if order.status == order.Completed:
            if order.isbuy():
                buytxt = 'BUY COMPLETE, %.2f' % order.executed.price
                self.log(buytxt, order.executed.dt)
            else:
                selltxt = 'SELL COMPLETE, %.2f' % order.executed.price
                self.log(selltxt, order.executed.dt)

        elif order.status in [order.Expired, order.Canceled, order.Margin]:
            self.log('%s ,' % order.Status[order.status])
            pass  # Simply log

        # Allow new orders
        self.orderid = None

def runstrat():
    args = parse_args()

    # Create a cerebro entity
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.set_coc(True)

    # Add a strategy
    cerebro.addstrategy(MyStrategy,
        printout = True)

    # Add observer
    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.BuySell)

    dataframe = td.TradeData().load_daily("TX", "Commodity")
    dataindex = td.TradeData().load_daily("TX", "Index")
    n1 = len(dataframe.columns)
    datajoin = pd.concat([dataframe, dataindex], axis=1, join='inner')

    dataframe = datajoin.ix[:, :n1]
    dataindex = datajoin.ix[:, n1:]
    if args.cut > 0:
        dataframe = dataframe.iloc[:args.cut]
        dataindex = dataindex.iloc[:args.cut]
    datadiff = dataframe - dataindex

    
    if not args.noprint:
        print('-dataframe-------------------------------------------------')
        print(dataframe)
        print('-dataindex-------------------------------------------------')
        print(dataindex)


    # Pass it to the backtrader datafeed and add it to the cerebro
    data = bt.feeds.PandasData(dataname=dataframe)
    data2 = bt.feeds.PandasData(dataname=dataindex)
    data3 = bt.feeds.PandasData(dataname=datadiff)

    data2.plotinfo.plot = None
    data2.plotinfo.plotmaster = data

    cerebro.adddata(data)
    cerebro.adddata(data2)
    cerebro.adddata(data3, name='diff')

    # Run over everything
    cerebro.run()

    # Plot the result
    scheme = PlotScheme()
    scheme.tickrotation = 0
    scheme.fmt_x_ticks = "%Y/%m"
    scheme.volume = False
    # cerebro.plot(scheme=scheme)
    scheme.rowsminor = 100
    cerebro.plot(scheme=scheme)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Pandas test script')

    parser.add_argument('--noheaders', action='store_true', default=False,
                        required=False,
                        help='Do not use header rows')

    parser.add_argument('--noprint', action='store_true', default=True,
                        help='Print the dataframe')

    parser.add_argument('--cut', '-c', type=int, default=0,
                        help='Cut the first samples for backtest, 0 for no-cut')

    return parser.parse_args()


if __name__ == '__main__':
    runstrat()
